"use client";
import { useState, useTransition } from "react";
import Link from "next/link";
import { requestInterviewFeedback } from "./actions";
import type { InterviewOperation } from "./types";

export function InterviewFeedback({
  sessionId,
  promptId,
  text,
  existing,
}: {
  sessionId: string;
  promptId: string;
  text: string;
  existing?: InterviewOperation;
}) {
  const [confirmed, setConfirmed] = useState(false);
  const [operation, setOperation] = useState(existing);
  const [operationId, setOperationId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [pending, transition] = useTransition();
  const feedback = operation?.feedback;
  return (
    <section className="space-y-3">
      <Link href="/settings/interviews">
        Enable or change interview AI consent
      </Link>
      {feedback ? (
        <>
          <h3>AI feedback</h3>
          {feedback.criteria.map((c) => (
            <p key={c.dimension}>
              <strong>{c.dimension}: </strong>
              {c.finding}
              {c.quote && <span> Evidence: “{c.quote}”</span>}
            </p>
          ))}
          <p>Uncertainty: {feedback.uncertainty}</p>
          <ul>
            {feedback.next_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ul>
          {feedback.follow_up && (
            <p>Reviewed follow-up selected: {feedback.follow_up}</p>
          )}
        </>
      ) : (
        <>
          <label className="block">
            <input
              type="checkbox"
              checked={confirmed}
              disabled={pending}
              onChange={(e) => setConfirmed(e.target.checked)}
            />{" "}
            I confirm the response shown above is the text I want assessed.
          </label>
          <button
            disabled={pending || !confirmed || !text.trim()}
            onClick={() =>
              transition(async () => {
                const id = operationId ?? crypto.randomUUID();
                setOperationId(id);
                setMessage("");
                try {
                  const result = await requestInterviewFeedback(
                    sessionId,
                    id,
                    promptId,
                    confirmed,
                  );
                  setOperation(result);
                  if (result.state !== "running") setOperationId(null);
                  if (result.state !== "complete")
                    setMessage(
                      `Feedback pending (${result.state.replaceAll("_", " ")}). Your response and reviewed rubric remain available. Retry manually later if quota and budget allow.`,
                    );
                } catch {
                  setMessage(
                    "AI feedback is unavailable. Check your own key, consent and session budget. Your response and self-review rubric are saved.",
                  );
                }
              })
            }
          >
            {pending
              ? "Requesting feedback…"
              : operation
                ? "Retry AI feedback"
                : "Request AI feedback"}
          </button>
          {operation && (
            <p>Saved status: {operation.state.replaceAll("_", " ")}</p>
          )}
        </>
      )}
      {message && <p role="status">{message}</p>}
    </section>
  );
}
