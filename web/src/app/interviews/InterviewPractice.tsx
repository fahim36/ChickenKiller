"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import {
  startInterview,
  saveInterviewResponse,
  deleteInterview,
} from "./actions";
import type { InterviewSession, Topics } from "./types";

export function InterviewPractice({
  stack,
  topics,
  history,
}: {
  stack: string;
  topics: Topics;
  history: InterviewSession[];
}) {
  const [current, setCurrent] = useState<InterviewSession | null>(null);
  const [sessions, setSessions] = useState(history);
  const [selected, setSelected] = useState<string[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [pending, transition] = useTransition();
  const prompt = current?.prompts.find((p) => !(p.id in current.responses));
  function run(action: () => Promise<void>) {
    setError("");
    transition(async () => {
      try {
        await action();
      } catch {
        setError(
          "The change could not be saved. Your text is still here; try again.",
        );
      }
    });
  }
  function save(value: string | null) {
    if (!current || !prompt) return;
    run(async () => {
      const updated = await saveInterviewResponse(current.id, prompt.id, value);
      setCurrent(updated);
      setSessions((rows) =>
        rows.map((row) => (row.id === updated.id ? updated : row)),
      );
      setText("");
    });
  }
  return (
    <section className="space-y-6">
      <p>
        Optional practice. This does not change quiz scores or progress. Private
        text expires after 30 days.
      </p>
      {error && <p role="alert">{error}</p>}
      {!current && (
        <>
          {topics.message ? (
            <p>
              {topics.message}{" "}
              {topics.lesson_id && (
                <Link
                  href={`/stacks/${encodeURIComponent(stack)}/lessons/${encodeURIComponent(topics.lesson_id)}`}
                >
                  Study the Lesson
                </Link>
              )}
            </p>
          ) : (
            <>
              <fieldset>
                <legend>
                  Choose up to three studied topics, or use the recommended
                  order
                </legend>
                {[
                  ...new Map(topics.topics.map((t) => [t.concept, t])).values(),
                ].map((t) => (
                  <label key={t.concept} className="block">
                    <input
                      type="checkbox"
                      checked={selected.includes(t.concept)}
                      disabled={
                        pending ||
                        (!selected.includes(t.concept) && selected.length >= 3)
                      }
                      onChange={(e) =>
                        setSelected(
                          e.target.checked
                            ? [...selected, t.concept]
                            : selected.filter((c) => c !== t.concept),
                        )
                      }
                    />{" "}
                    {t.concept}
                  </label>
                ))}
              </fieldset>
              <button
                disabled={pending}
                onClick={() =>
                  run(async () => {
                    const row = await startInterview(stack, selected);
                    setCurrent(row);
                    setSessions((rows) => [row, ...rows]);
                  })
                }
              >
                Start practice
              </button>
            </>
          )}
        </>
      )}
      {current && (
        <>
          <p>
            History expires {new Date(current.expires_at).toLocaleDateString()}.
          </p>
          {prompt ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                save(text);
              }}
            >
              <h2>{prompt.scenario}</h2>
              <label className="block">
                Your response (optional)
                <textarea
                  maxLength={12000}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  className="block w-full border rounded p-3"
                  disabled={pending}
                />
              </label>
              <button disabled={pending} type="submit">
                Save and self-review
              </button>{" "}
              <button
                disabled={pending}
                type="button"
                onClick={() => save(null)}
              >
                Skip scenario
              </button>
            </form>
          ) : (
            <p role="status">
              Practice complete. Use the rubrics below to choose what to
              improve.
            </p>
          )}
          {current.prompts
            .filter((p) => p.id in current.responses)
            .map((p) => (
              <article key={p.id} className="border rounded p-4">
                <h2>{p.scenario}</h2>
                <p>{current.responses[p.id] ?? "Skipped — no assessment."}</p>
                <h3>Reviewed self-review rubric</h3>
                <ul>
                  {p.rubric.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
                <h3>Common misconceptions</h3>
                <ul>
                  {p.misconceptions.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
                <Link
                  href={`/stacks/${encodeURIComponent(current.stack_id)}/lessons/${encodeURIComponent(p.lesson)}`}
                >
                  Review the Lesson
                </Link>
              </article>
            ))}
          <button
            disabled={pending}
            onClick={() => {
              setCurrent(null);
              setText("");
            }}
          >
            Back to practice list
          </button>
        </>
      )}
      <h2>Private history</h2>
      {sessions
        .filter((s) => s.stack_id === stack)
        .map((s) => (
          <div key={s.id} className="flex gap-4">
            <button
              disabled={pending}
              onClick={() => {
                setCurrent(s);
                setText("");
              }}
            >
              Open session · {s.prompts.length} scenarios
            </button>
            <button
              disabled={pending}
              onClick={() =>
                run(async () => {
                  await deleteInterview(s.id);
                  setSessions((rows) => rows.filter((row) => row.id !== s.id));
                  if (current?.id === s.id) setCurrent(null);
                })
              }
            >
              Delete session
            </button>
          </div>
        ))}
    </section>
  );
}
