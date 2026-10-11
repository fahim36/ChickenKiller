"use client";
import { useState, useTransition } from "react";
import Link from "next/link";
import { updateInterviewSettings } from "./actions";

export interface InterviewSettings {
  enabled: boolean;
  processing_consent: boolean;
  free_project_confirmed: boolean;
}

export function InterviewSettingsForm({
  initial,
}: {
  initial: InterviewSettings;
}) {
  const [settings, setSettings] = useState(initial);
  const [message, setMessage] = useState("");
  const [pending, transition] = useTransition();
  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        transition(async () => {
          try {
            setSettings(await updateInterviewSettings(settings));
            setMessage("Interview settings saved.");
          } catch {
            setMessage(
              "Settings could not be saved. Check that you have saved your own Gemini key.",
            );
          }
        });
      }}
    >
      <p>
        Interviews use only your own saved Gemini Developer API key.{" "}
        <Link href="/settings">Save or remove your key in Settings</Link>.
        Changing that key requires confirming interview use again.
      </p>
      <label className="block">
        <input
          type="checkbox"
          checked={settings.enabled}
          disabled={pending}
          onChange={(e) =>
            setSettings({ ...settings, enabled: e.target.checked })
          }
        />{" "}
        Enable my own Gemini key for interviews
      </label>
      <label className="block">
        <input
          type="checkbox"
          checked={settings.free_project_confirmed}
          disabled={pending}
          onChange={(e) =>
            setSettings({
              ...settings,
              free_project_confirmed: e.target.checked,
            })
          }
        />{" "}
        I confirm this key belongs to a Free Tier project with billing disabled.
      </label>
      <p>
        This confirmation is your attestation. The app cannot verify billing
        from the key or guarantee zero billing. Check your project in Google AI
        Studio. Quotas are shared with other uses of that project.
      </p>
      <label className="block">
        <input
          type="checkbox"
          checked={settings.processing_consent}
          disabled={pending}
          onChange={(e) =>
            setSettings({ ...settings, processing_consent: e.target.checked })
          }
        />{" "}
        I consent to sending interview transcripts and, when required,
        recordings to Google for processing.
      </label>
      <p>
        Gemini free-tier processing includes product-improvement use. Google&apos;s
        retention and processing are separate from the app&apos;s 30-day private
        history and temporary audio deletion. Decline or disable AI to keep
        reviewed self-review available.
      </p>
      <p>
        Each session permits at most 18 Gemini attempts, including failures and
        transcription. No automatic quota retries or fallback keys.
      </p>
      <button disabled={pending} type="submit">
        Save interview settings
      </button>
      {message && <p role="status">{message}</p>}
    </form>
  );
}

