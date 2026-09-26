import { afterEach, expect, it, vi } from "vitest";
import { saveSettings } from "./actions";

vi.mock("next/cache", () => ({ revalidatePath: () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => vi.unstubAllGlobals());

function form(activeStackId: string, timeZone: string): FormData {
  const data = new FormData();
  data.set("active_stack_id", activeStackId);
  data.set("time_zone", timeZone);
  return data;
}

it("saves the Active Stack and time zone, then lands on that Stack", async () => {
  const fetch = vi.fn(async () => Response.json({}));
  vi.stubGlobal("fetch", fetch);

  const result = saveSettings(null, form("agentic-ai-engineer", " Asia/Dhaka "));

  await expect(result).rejects.toThrow(
    expect.objectContaining({ digest: expect.stringContaining("/stacks/agentic-ai-engineer") }),
  );
  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/me/settings",
    expect.objectContaining({
      method: "PUT",
      body: JSON.stringify({ active_stack_id: "agentic-ai-engineer", time_zone: "Asia/Dhaka" }),
    }),
  );
});

it("asks for a real time zone when the API rejects the name", async () => {
  const detail = [{ loc: ["body", "time_zone"], msg: "Value error, Choose a time zone" }];
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail }, { status: 422 })));

  expect(await saveSettings(null, form("agentic-ai-engineer", "Mars/Base"))).toEqual({
    error: "“Mars/Base” isn't a time zone. Pick one from the list, such as Asia/Dhaka.",
  });
});

it("shows the API's reason when the Stack can't be chosen", async () => {
  const detail = "Choose one of the published Stacks.";
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail }, { status: 422 })));

  expect(await saveSettings(null, form("draft-stack", "Asia/Dhaka"))).toEqual({ error: detail });
});
