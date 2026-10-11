// Local, isolated Chromium smoke. Synthetic microphone; mocked Server Actions; no keys/providers.
import { mkdtemp, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import { createServer as createPortProbe } from "node:net";
import { createServer } from "vite";
import react from "@vitejs/plugin-react";

const web = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const workspace = resolve(web, "..");
const temporary = await mkdtemp(resolve(tmpdir(), "interview-browser-"));
const artifacts = resolve(workspace, ".scratch/mock-interviews/browser-smoke");
await mkdir(artifacts, { recursive: true });
const slash = (path) => path.replaceAll("\\", "/");
const actions = resolve(temporary, "actions.js");
// Refuse a busy debugging port rather than attaching to an existing personal browser.
await new Promise((resolve, reject) => {
  const probe = createPortProbe();
  probe.once("error", reject);
  probe.listen(9228, "127.0.0.1", () => probe.close(resolve));
});
await writeFile(
  actions,
  `
let clip, audio;
window.interviewEvents = [];
export async function uploadInterviewAudio(session, prompt, id, form) {
  const file = form.get("audio");
  const bytes = new Uint8Array(await file.arrayBuffer());
  audio = { mime: file.type, data: btoa(String.fromCharCode(...bytes)) };
  window.syntheticRecording = { ...audio };
  window.interviewEvents.push({ event: "upload", bytes: file.size, mime: file.type });
  clip = { id, prompt_id: prompt, expires_at: new Date(Date.now() + 3600000).toISOString(), transcript: null };
  return clip;
}
export async function loadInterviewAudio() { return audio; }
export async function transcribeInterviewAudio() {
  window.interviewEvents.push({ event: "transcribe" });
  clip = { ...clip, transcript: "Use a taken.", state: "complete" }; return clip;
}
export async function confirmInterviewTranscript(session, recording, prompt, text) {
  window.interviewEvents.push({ event: "confirm", text }); audio = null;
  return { id: session, stack_id: "python", prompts: [], responses: { [prompt]: text } };
}
export async function cancelInterviewAudio() { audio = null; }
`,
);
await writeFile(
  resolve(temporary, "index.html"),
  `<!doctype html><html lang="en"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Interview browser verification</title><div id="root"></div><script type="module" src="/main.jsx"></script></html>`,
);
await writeFile(
  resolve(temporary, "main.jsx"),
  `
import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { VoiceResponse } from "/@fs/${slash(resolve(web, "src/app/interviews/VoiceResponse.tsx"))}";
import { DeviceSpeech } from "/@fs/${slash(resolve(web, "src/app/interviews/DeviceSpeech.tsx"))}";
function App() {
  const [confirmed, setConfirmed] = useState(null);
  return <main><h1>Explain competing database updates</h1>
    <DeviceSpeech text="Explain competing database updates" />
    <VoiceResponse sessionId="synthetic-session" promptId="synthetic-main"
      onConfirmed={row => setConfirmed(row.responses["synthetic-main"])} />
    {confirmed && <p id="confirmed">Confirmed response: {confirmed}</p>}
  </main>;
}
createRoot(document.getElementById("root")).render(<App />);
`,
);
const server = await createServer({
  configFile: false,
  root: temporary,
  resolve: {
    alias: {
      react: resolve(web, "node_modules/react"),
      "react-dom": resolve(web, "node_modules/react-dom"),
    },
  },
  plugins: [
    react(),
    {
      name: "interview-action-fixtures",
      enforce: "pre",
      resolveId(source, importer) {
        if (
          source === "./actions" &&
          importer?.includes("/src/app/interviews/")
        )
          return actions;
      },
    },
  ],
  server: {
    host: "127.0.0.1",
    port: 4179,
    strictPort: true,
    watch: { ignored: ["**/profile/**"] },
    fs: { allow: [temporary, web] },
  },
});
await server.listen();
const browserPath =
  process.env.INTERVIEW_BROWSER ??
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const browser = spawn(
  browserPath,
  [
    "--headless=new",
    "--no-first-run",
    "--no-default-browser-check",
    "--use-fake-ui-for-media-stream",
    "--use-fake-device-for-media-stream",
    `--user-data-dir=${slash(resolve(temporary, "profile"))}`,
    "--remote-debugging-port=9228",
    "http://127.0.0.1:4179",
  ],
  { windowsHide: true, stdio: "ignore" },
);
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
let socket;
try {
  let targets;
  for (let attempt = 0; attempt < 100; attempt++) {
    try {
      targets = await (await fetch("http://127.0.0.1:9228/json")).json();
      break;
    } catch {
      await delay(100);
    }
  }
  const target = targets?.find(
    (row) => row.type === "page" && row.url.startsWith("http://127.0.0.1:4179"),
  );
  if (!target) throw Error("Isolated browser did not start");
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve);
    socket.addEventListener("error", reject);
  });
  let sequence = 0;
  const pending = new Map();
  socket.addEventListener("message", (event) => {
    const response = JSON.parse(event.data);
    if (!response.id) return;
    const call = pending.get(response.id);
    if (!call) return;
    pending.delete(response.id);
    if (response.error) call.reject(Error(response.error.message));
    else call.resolve(response.result);
  });
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const id = ++sequence;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
  const evaluate = async (expression) => {
    const result = await send("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true,
    });
    if (result.exceptionDetails) throw Error(result.exceptionDetails.text);
    return result.result.value;
  };
  const waitFor = async (expression) => {
    for (let attempt = 0; attempt < 300; attempt++) {
      if (await evaluate(`Boolean(${expression})`)) return;
      await delay(100);
    }
    throw Error(
      `Browser condition timed out: ${expression}; ${await evaluate("document.body.textContent.slice(0, 1600)")}`,
    );
  };
  const button = (name) =>
    `Array.from(document.querySelectorAll("button")).find(b => b.textContent.trim() === ${JSON.stringify(name)})`;
  const click = async (name) => {
    await waitFor(`${button(name)} && !${button(name)}.disabled`);
    await evaluate(`${button(name)}.click()`);
  };
  const reports = [];
  for (const [mode, width, height, mobile] of [
    ["desktop", 1280, 900, false],
    ["mobile-viewport", 390, 844, true],
  ]) {
    await send("Emulation.setDeviceMetricsOverride", {
      width,
      height,
      deviceScaleFactor: 1,
      mobile,
    });
    await send("Page.navigate", { url: "http://127.0.0.1:4179" });
    await waitFor(`${button("Start recording")}`);
    await evaluate(`${button("Start recording")}.focus()`);
    await send("Input.dispatchKeyEvent", {
      type: "keyDown",
      key: "Enter",
      code: "Enter",
      windowsVirtualKeyCode: 13,
    });
    await send("Input.dispatchKeyEvent", {
      type: "char",
      text: "\r",
      key: "Enter",
      code: "Enter",
      windowsVirtualKeyCode: 13,
    });
    await send("Input.dispatchKeyEvent", {
      type: "keyUp",
      key: "Enter",
      code: "Enter",
      windowsVirtualKeyCode: 13,
    });
    await waitFor('document.body.textContent.includes("Microphone recording")');
    await delay(800);
    await click("Stop recording");
    await waitFor('document.querySelector("audio")');
    const recorded = await evaluate("window.syntheticRecording");
    await writeFile(
      resolve(artifacts, `${mode}.webm`),
      Buffer.from(recorded.data, "base64"),
    );
    await evaluate(
      'document.querySelector("audio").play().catch(() => undefined)',
    );
    await click("Transcribe with my Gemini key");
    await waitFor(
      'document.querySelector("textarea")?.value === "Use a taken."',
    );
    await evaluate(`(() => {
      const area = document.querySelector("textarea");
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set.call(area, "Corrected concurrency token.");
      area.dispatchEvent(new Event("input", { bubbles: true }));
    })()`);
    await click("Confirm transcript and delete audio");
    await waitFor(
      'document.querySelector("#confirmed")?.textContent.includes("Corrected concurrency token.")',
    );
    const result = await evaluate(
      `({ events: window.interviewEvents, audioDeleted: !document.querySelector("audio"), microphoneOff: document.body.textContent.includes("Microphone off"), userAgent: navigator.userAgent, mediaRecorder: typeof MediaRecorder, supported: ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"].filter(t => MediaRecorder.isTypeSupported(t)), horizontalOverflow: document.documentElement.scrollWidth > innerWidth })`,
    );
    if (
      !result.audioDeleted ||
      !result.microphoneOff ||
      result.events.length !== 3
    )
      throw Error("Recording lifecycle assertion failed");
    reports.push({ mode, width, height, ...result });
    const screenshot = await send("Page.captureScreenshot", { format: "png" });
    await writeFile(
      resolve(artifacts, `${mode}.png`),
      Buffer.from(screenshot.data, "base64"),
    );
  }
  const report = {
    generatedAt: new Date().toISOString(),
    syntheticMicrophone: true,
    mockedActions: true,
    realProviderCalls: 0,
    modes: reports,
    limitations: [
      "Mobile viewport uses desktop Chromium; physical Android/iOS and Safari are not measured.",
      "Synthetic audio does not measure accent transcription quality.",
    ],
  };
  await writeFile(
    resolve(artifacts, "report.json"),
    JSON.stringify(report, null, 2),
  );
  console.log(JSON.stringify(report));
  await send("Browser.close");
} finally {
  socket?.close();
  browser.kill();
  await server.close();
}
