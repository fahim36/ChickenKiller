"use client";
import { useEffect, useRef, useState, useTransition } from "react";
import {
  cancelInterviewAudio,
  confirmInterviewTranscript,
  loadInterviewAudio,
  transcribeInterviewAudio,
  uploadInterviewAudio,
} from "./actions";
import type { InterviewRecording, InterviewSession } from "./types";

export function VoiceResponse({
  sessionId,
  promptId,
  initial,
  onConfirmed,
  seconds = 90,
}: {
  sessionId: string;
  promptId: string;
  initial?: InterviewRecording;
  onConfirmed: (row: InterviewSession) => void;
  seconds?: 90 | 45 | 60;
}) {
  const [clip, setClip] = useState(initial);
  const [playback, setPlayback] = useState<string | null>(null);
  const [transcript, setTranscript] = useState(initial?.transcript ?? "");
  const [recording, setRecording] = useState(false);
  const [acquiring, setAcquiring] = useState(false);
  const [message, setMessage] = useState("");
  const [pending, transition] = useTransition();
  const [elapsed, setElapsed] = useState(0);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tick = useRef<ReturnType<typeof setInterval> | null>(null);
  const mounted = useRef(true);
  const canceled = useRef(false);
  const operationId = useRef<string | null>(null);
  const acquiringRef = useRef(false);
  useEffect(() => {
    if (!clip) return;
    const timeout = setTimeout(
      () => {
        setPlayback(null);
        setClip(undefined);
        setTranscript("");
        setMessage(
          "Audio has expired. Use typing or rerecord within turn limits.",
        );
      },
      Math.max(0, Date.parse(clip.expires_at) - Date.now()),
    );
    return () => clearTimeout(timeout);
  }, [clip]);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      canceled.current = true;
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach((t) => t.stop());
      if (timer.current) clearTimeout(timer.current);
      if (tick.current) clearInterval(tick.current);
    };
  }, []);
  function run(action: () => Promise<void>) {
    setMessage("");
    transition(async () => {
      try {
        await action();
      } catch {
        if (mounted.current)
          setMessage(
            "Voice processing is unavailable. Keep playback for self-review, type your response, or check your AI consent and quota.",
          );
      }
    });
  }
  async function start() {
    if (acquiringRef.current || recording || pending) return;
    setMessage("");
    canceled.current = false;
    if (
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === "undefined"
    ) {
      setMessage(
        "Recording is unavailable on this browser. Use the typing option.",
      );
      return;
    }
    acquiringRef.current = true;
    setAcquiring(true);
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!mounted.current) {
        media.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current = media;
      const mime = [
        "audio/webm;codecs=opus",
        "audio/mp4",
        "audio/ogg;codecs=opus",
      ].find((t) => MediaRecorder.isTypeSupported(t));
      if (!mime) {
        media.getTracks().forEach((t) => t.stop());
        setMessage("No supported recording format. Use typing.");
        return;
      }
      const instance = new MediaRecorder(media, {
        mimeType: mime,
        audioBitsPerSecond: 96000,
      });
      recorder.current = instance;
      const chunks: Blob[] = [];
      instance.ondataavailable = (e) => {
        if (e.data.size) chunks.push(e.data);
      };
      instance.onstop = () => {
        media.getTracks().forEach((t) => t.stop());
        if (timer.current) clearTimeout(timer.current);
        if (tick.current) clearInterval(tick.current);
        if (!mounted.current || canceled.current) return;
        setRecording(false);
        const blob = new Blob(chunks, { type: instance.mimeType });
        run(async () => {
          const form = new FormData();
          form.set("audio", blob, "response");
          const saved = await uploadInterviewAudio(
            sessionId,
            promptId,
            crypto.randomUUID(),
            form,
          );
          if (!mounted.current) {
            await cancelInterviewAudio(sessionId, saved.id);
            return;
          }
          setPlayback(null);
          setClip(saved);
          setTranscript("");
          operationId.current = null;
          const audio = await loadInterviewAudio(sessionId, saved.id);
          if (audio && mounted.current)
            setPlayback(`data:${audio.mime};base64,${audio.data}`);
        });
      };
      instance.onerror = () => {
        canceled.current = true;
        if (timer.current) clearTimeout(timer.current);
        if (tick.current) clearInterval(tick.current);
        if (instance.state === "recording") instance.stop();
        media.getTracks().forEach((t) => t.stop());
        setMessage("Recording failed. Use typing or try again.");
        setRecording(false);
      };
      setElapsed(0);
      setRecording(true);
      instance.start();
      tick.current = setInterval(() => setElapsed((n) => n + 1), 1000);
      timer.current = setTimeout(
        () => {
          if (instance.state === "recording") instance.stop();
        },
        (seconds - 0.5) * 1000,
      );
    } catch {
      stream.current?.getTracks().forEach((t) => t.stop());
      setMessage(
        "Microphone access is unavailable or refused. Use the typing option.",
      );
    } finally {
      acquiringRef.current = false;
      if (mounted.current) setAcquiring(false);
    }
  }
  return (
    <section
      aria-label="Voice response"
      className="space-y-3 border rounded p-4"
    >
      <p>
        English voice response · up to {seconds} seconds · one replacement
        recording. Audio expires within 24 hours and is deleted after transcript
        confirmation.
      </p>
      <p>
        Transcription uses your enabled Gemini key and one request from the
        shared session budget. Server Whisper is disabled until recording
        quality and server capacity are verified. Playback and typing remain
        available. Deleting audio here does not control Google’s processing of
        submitted audio.
      </p>
      <p role="status">
        {recording
          ? `Microphone recording: ${elapsed} seconds`
          : pending
            ? "Processing voice response…"
            : acquiring
              ? "Waiting for microphone permission…"
              : "Microphone off"}
      </p>
      {recording ? (
        <>
          <button type="button" onClick={() => recorder.current?.stop()}>
            Stop recording
          </button>
          <button
            type="button"
            onClick={() => {
              canceled.current = true;
              recorder.current?.stop();
              setRecording(false);
            }}
          >
            Cancel recording
          </button>
        </>
      ) : (
        <button type="button" disabled={pending || acquiring} onClick={start}>
          {clip ? "Replace recording" : "Start recording"}
        </button>
      )}
      {clip && (
        <>
          <p>Audio expires {new Date(clip.expires_at).toLocaleString()}.</p>
          <button
            type="button"
            disabled={pending || recording}
            onClick={() =>
              run(async () => {
                const audio = await loadInterviewAudio(sessionId, clip.id);
                if (!audio) {
                  setPlayback(null);
                  setMessage("Audio has expired or was deleted.");
                  return;
                }
                setPlayback(`data:${audio.mime};base64,${audio.data}`);
              })
            }
          >
            Load playback
          </button>
          {playback && (
            <audio
              controls
              src={playback}
              aria-label="Your temporary response recording"
            />
          )}
          <button
            type="button"
            disabled={pending || recording || !!clip.transcript}
            onClick={() =>
              run(async () => {
                const id = operationId.current ?? crypto.randomUUID();
                operationId.current = id;
                const result = await transcribeInterviewAudio(
                  sessionId,
                  clip.id,
                  id,
                );
                setClip(result);
                if (result.state !== "running") operationId.current = null;
                if (result.transcript) setTranscript(result.transcript);
                else
                  setMessage(
                    `No confirmed transcript (${result.state ?? "unavailable"}). Keep playback, type your response or retry manually later.`,
                  );
              })
            }
          >
            Transcribe with my Gemini key
          </button>
          <label className="block">
            Confirm or correct your transcript
            <textarea
              className="block border p-3 w-full"
              maxLength={12000}
              value={transcript}
              disabled={pending}
              onChange={(e) => setTranscript(e.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={pending || recording || !transcript.trim()}
            onClick={() =>
              run(async () => {
                const row = await confirmInterviewTranscript(
                  sessionId,
                  clip.id,
                  promptId,
                  transcript,
                );
                setPlayback(null);
                setClip(undefined);
                onConfirmed(row);
              })
            }
          >
            Confirm transcript and delete audio
          </button>
          <button
            type="button"
            disabled={pending || recording}
            onClick={() =>
              run(async () => {
                await cancelInterviewAudio(sessionId, clip.id);
                setClip(undefined);
                setPlayback(null);
                setTranscript("");
              })
            }
          >
            Discard stored recording
          </button>
        </>
      )}
      {message && <p role="alert">{message}</p>}
    </section>
  );
}
