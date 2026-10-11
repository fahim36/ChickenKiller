"use client";
import { useState, useTransition } from "react";
import { openInterviewTurn } from "./actions";
import type { InterviewPrompt, InterviewSession } from "./types";

export function GuidedOptions({
  session,
  prompt,
  onOpened,
}: {
  session: InterviewSession;
  prompt: InterviewPrompt;
  onOpened: (session: InterviewSession) => void;
}) {
  const [pending, transition] = useTransition();
  const [message, setMessage] = useState("");
  const siblings = (session.turns ?? []).filter(
    (t) => t.parent_id === prompt.id,
  );
  const retry = siblings.some((t) => t.kind === "retry");
  const followUp = siblings.some((t) => t.kind === "follow_up");
  const open = (session.turns ?? []).some((t) => !(t.id in session.responses));
  const assessment = session.operations?.find(
    (o) => o.prompt_id === prompt.id && o.state === "complete" && o.feedback,
  );
  const options = (prompt.follow_ups ?? []).filter(
    (f) => !assessment || assessment.feedback?.follow_up === f.id,
  );
  function start(kind: "follow_up" | "retry", id?: string) {
    transition(async () => {
      setMessage("");
      try {
        onOpened(await openInterviewTurn(session.id, prompt.id, kind, id));
      } catch {
        setMessage(
          "This optional turn is unavailable. Finish an open turn or use the reviewed rubric.",
        );
      }
    });
  }
  return (
    <section aria-label="Optional guided practice" className="space-y-2">
      <p>
        Optional practice: one reviewed follow-up, then one retry of the main
        scenario. Skipping does not mark you wrong.
      </p>
      {!followUp && !retry && options.length > 0 && (
        <>
          <p>
            {assessment
              ? "AI selected this reviewed follow-up:"
              : "Self-review: choose a reviewed follow-up. This makes no AI request."}
          </p>
          {options.map((f) => (
            <button
              type="button"
              key={f.id}
              disabled={pending || open}
              onClick={() => start("follow_up", f.id)}
            >
              {f.scenario} · Practice follow-up
            </button>
          ))}
        </>
      )}
      {!retry && (
        <button
          type="button"
          disabled={pending || open}
          onClick={() => start("retry")}
        >
          Retry the main scenario
        </button>
      )}
      {message && <p role="status">{message}</p>}
    </section>
  );
}
