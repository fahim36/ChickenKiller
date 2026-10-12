"use client";

import Link from "next/link";
import { Inline } from "@/components/Inline";
import { useRef, useState } from "react";
import { abandonPlacement, savePlacement, submitPlacement } from "./actions";
import type { PlacementAttempt } from "./types";

function PlacementText({ text }: { text: string }) {
  return text.split(/```[\w+-]*\n([\s\S]*?)```/g).map((part, index) =>
    index % 2 ? (
      <code
        key={index}
        className="my-2 block overflow-x-auto whitespace-pre-wrap rounded bg-muted p-3 text-sm"
      >
        {part}
      </code>
    ) : (
      <Inline key={index} text={part} />
    ),
  );
}

export function PlacementPractice({ initial }: { initial: PlacementAttempt }) {
  const [attempt, setAttempt] = useState(initial);
  const [answers, setAnswers] = useState(initial.responses);
  const answersRef = useRef(initial.responses);
  const queue = useRef(Promise.resolve());
  const dirty = useRef(new Set<string>());
  const [pending, setPending] = useState(0);
  const [error, setError] = useState("");
  const [unsaved, setUnsaved] = useState(false);

  function save(question: string, answer: string | string[] | null) {
    const next = { ...answersRef.current, [question]: answer };
    answersRef.current = next;
    setAnswers(next);
    dirty.current.add(question);
    setUnsaved(true);
    setPending((n) => n + 1);
    queue.current = queue.current.then(async () => {
      try {
        const result = await savePlacement(attempt.id, question, answer);
        if (result.state !== "open") setAttempt(result);
        if (answersRef.current[question] === answer)
          dirty.current.delete(question);
        if (dirty.current.size === 0) {
          setError("");
          setUnsaved(false);
        }
      } catch {
        setError(
          "Some answers could not be saved. Retry before leaving this page.",
        );
      } finally {
        setPending((n) => n - 1);
      }
    });
  }

  async function abandon() {
    try {
      const result = await abandonPlacement(attempt.id);
      setAttempt(result);
    } catch {
      setError("Could not abandon this attempt. Try again.");
    }
  }

  async function submit() {
    setPending((n) => n + 1);
    try {
      setAttempt(await submitPlacement(attempt.id));
    } catch {
      setError(
        "Could not submit. Your saved answers remain available; try again.",
      );
    } finally {
      setPending((n) => n - 1);
    }
  }

  return (
    <div className="min-w-0 space-y-6 break-words">
      <p>
        Self-assessment: answer without outside help. No timer. Answers save
        automatically; correctness appears after submission.
      </p>
      <p role="status">
        {pending
          ? "Saving answers…"
          : error
            ? "Unsaved answers"
            : "Answers saved"}
      </p>
      {error && (
        <div role="alert">
          <p>{error}</p>
          <button
            type="button"
            onClick={() => {
              for (const question of dirty.current)
                save(question, answersRef.current[question] ?? null);
            }}
          >
            Retry saving
          </button>
        </div>
      )}
      {attempt.state === "submitted" && attempt.result ? (
        <div className="space-y-4">
          <h2>
            {attempt.result.passed
              ? "Placement passed"
              : "Continue the Lesson path"}
          </h2>
          <p>
            {attempt.result.correct}/{attempt.result.total} correct. Passing
            requires 80% overall and in every Lesson.
          </p>
          {attempt.result.lessons.map((lesson) => (
            <p key={lesson.lesson}>
              {lesson.lesson}: {lesson.correct}/{lesson.total} ·{" "}
              {lesson.passed ? "Passed" : "Below 80%"}
            </p>
          ))}
          <p>
            {attempt.result.passed
              ? "Previously incomplete Lessons are completed by placement."
              : "No additional Lessons were completed."}{" "}
            Misses are available in optional Review.
          </p>
          {attempt.questions.map((q) => (
            <section key={q.id} className="rounded border p-4">
              <h3>
                <PlacementText text={q.prompt} />
              </h3>
              <p>
                {attempt.result?.correct_questions[q.id]
                  ? "Correct"
                  : "Incorrect or unanswered"}
              </p>
              <p>
                Correct choices:{" "}
                {q.choices
                  .filter((c) => (q.answers ?? [q.answer]).includes(c.id))
                  .map((c) => c.text)
                  .join("; ")}
              </p>
              <p>{q.explanation}</p>
              {q.sources?.map((source) => (
                <p key={source.url}>
                  <a href={source.url}>{source.title}</a>
                </p>
              ))}
            </section>
          ))}
          <Link href="/review">Optional Review</Link>
        </div>
      ) : attempt.state !== "open" ? (
        <p>{attempt.reason ?? "This attempt has finished."}</p>
      ) : (
        <>
          {attempt.questions.map((q, index) => (
            <fieldset
              key={q.id}
              className="min-w-0 rounded border p-4 space-y-3"
            >
              <legend className="max-w-full">
                {index + 1}. <PlacementText text={q.prompt} />
              </legend>
              <p>
                {q.lesson} ·{" "}
                {q.type === "multiple_select"
                  ? "Select all that apply"
                  : "Choose one"}
              </p>
              {q.choices.map((choice) => {
                const current = answers[q.id];
                const checked = Array.isArray(current)
                  ? current.includes(choice.id)
                  : current === choice.id;
                return (
                  <label key={choice.id} className="flex gap-2">
                    <input
                      type={q.type === "multiple_select" ? "checkbox" : "radio"}
                      name={q.id}
                      checked={checked}
                      onChange={() => {
                        const ticks = Array.isArray(current) ? current : [];
                        save(
                          q.id,
                          q.type === "multiple_select"
                            ? checked
                              ? ticks.filter((id) => id !== choice.id)
                              : [...ticks, choice.id]
                            : choice.id,
                        );
                      }}
                    />
                    <Inline text={choice.text} />
                  </label>
                );
              })}
              <button type="button" onClick={() => save(q.id, null)}>
                Clear answer
              </button>
            </fieldset>
          ))}
          <button
            type="button"
            disabled={pending > 0 || unsaved}
            onClick={submit}
          >
            Submit placement
          </button>
          <p>
            Submission is final. Unanswered Questions count as incorrect. One
            submitted attempt is allowed per Week teaching revision.
          </p>
          <button type="button" disabled={pending > 0} onClick={abandon}>
            Abandon attempt
          </button>
          <p>
            Abandoning uses no submitted attempt, but viewed Questions remain
            seen.
          </p>
        </>
      )}
      <Link href={`/stacks/${encodeURIComponent(attempt.stack_id)}`}>
        Return to your Week map
      </Link>
    </div>
  );
}
