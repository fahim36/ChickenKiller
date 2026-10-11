"use client";
import { useEffect, useState } from "react";

export function DeviceSpeech({ text }: { text: string }) {
  const [message, setMessage] = useState("");
  useEffect(
    () => () => {
      window.speechSynthesis?.cancel();
    },
    [],
  );
  return (
    <>
      <button
        type="button"
        onClick={() => {
          if (!window.speechSynthesis) {
            setMessage("Device speech is unavailable. Read the visible text.");
            return;
          }
          try {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = "en-US";
            utterance.onerror = () =>
              setMessage(
                "Speech playback is unavailable. Read the visible text.",
              );
            window.speechSynthesis.speak(utterance);
          } catch {
            setMessage(
              "Speech playback is unavailable. Read the visible text.",
            );
          }
        }}
      >
        Read aloud
      </button>
      {message && <p role="status">{message}</p>}
    </>
  );
}
