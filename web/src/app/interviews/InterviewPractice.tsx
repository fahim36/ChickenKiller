"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import {
  startInterview,
  saveInterviewResponse,
  deleteInterview,
} from "./actions";
import type { InterviewSession, Topics } from "./types";
import { InterviewFeedback } from "./InterviewFeedback";
import { VoiceResponse } from "./VoiceResponse";
import { DeviceSpeech } from "./DeviceSpeech";
import { GuidedOptions } from "./GuidedOptions";

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
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [pending, transition] = useTransition();
  const prompt =
    current?.turns?.find((p) => !(p.id in current.responses)) ??
    current?.prompts.find((p) => !(p.id in current.responses));
  const draftKey = `${current?.id ?? ""}:${prompt?.id ?? ""}`;
  const text = drafts[draftKey] ?? "";
  function setText(value: string) {
    setDrafts((rows) => ({ ...rows, [draftKey]: value }));
  }
  function update(row: InterviewSession) {
    setCurrent(row);
    setSessions((rows) => rows.map((s) => (s.id === row.id ? row : s)));
  }
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
              {prompt.kind && (
                <p>
                  {prompt.kind === "follow_up"
                    ? "Reviewed follow-up"
                    : "Practice retry of the main scenario"}
                </p>
              )}
              <DeviceSpeech text={prompt.scenario} />
              <VoiceResponse
                key={`${current.id}-${prompt.id}`}
                sessionId={current.id}
                promptId={prompt.id}
                seconds={prompt.seconds ?? 90}
                initial={current.recordings?.find(
                  (r) => r.prompt_id === prompt.id,
                )}
                onConfirmed={update}
              />
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
                {prompt.kind ? "Skip optional turn" : "Skip scenario"}
              </button>
            </form>
          ) : (
            <p role="status">
              Practice complete. Use the rubrics and teaching Lessons below to
              choose your next topic. Optional follow-ups and retries remain
              available.
            </p>
          )}
          {[...current.prompts, ...(current.turns ?? [])]
            .filter((p) => p.id in current.responses)
            .map((p) => (
              <article key={p.id} className="border rounded p-4">
                <h2>{p.scenario}</h2>
                <p>{current.responses[p.id] ?? "Skipped — no assessment."}</p>
                {p.kind === "retry" && p.parent_id && (
                  <p>
                    Earlier main response: {current.responses[p.parent_id]}.
                    Compare the explanations against the rubric and quoted
                    feedback. A repeated answer alone does not establish
                    improvement.
                  </p>
                )}
                {current.responses[p.id] && (
                  <InterviewFeedback
                    key={`${current.id}-${p.id}`}
                    sessionId={current.id}
                    promptId={p.id}
                    text={current.responses[p.id] ?? ""}
                    existing={current.operations?.find(
                      (op) => op.prompt_id === p.id && op.state === "complete",
                    )}
                    onResult={(operation) => {
                      const merge = (
                        row: InterviewSession,
                      ): InterviewSession =>
                        row.id === current.id
                          ? {
                              ...row,
                              operations: [
                                ...(row.operations ?? []).filter(
                                  (o) => o.id !== operation.id,
                                ),
                                operation,
                              ],
                            }
                          : row;
                      setCurrent((row) => (row ? merge(row) : null));
                      setSessions((rows) => rows.map(merge));
                    }}
                  />
                )}
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
                {!p.kind && current.responses[p.id] && (
                  <GuidedOptions
                    session={current}
                    prompt={p}
                    onOpened={update}
                  />
                )}
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
