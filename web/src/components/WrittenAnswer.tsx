"use client";

import type { QuizQuestion } from "@/lib/api";

/** The text box a written Question is answered in, in a Lesson Quiz or a Retake. */
export function WrittenAnswer({
  question,
  value,
  maxLength,
  onChange,
  idPrefix = "answer",
}: {
  question: QuizQuestion;
  value: string;
  maxLength: number;
  onChange: (value: string) => void;
  idPrefix?: string;
}) {
  const id = `${idPrefix}-${question.id}`;
  return (
    <>
      <label htmlFor={id} className="muted">
        Your answer
      </label>
      <textarea
        id={id}
        name={question.id}
        className="written-answer"
        rows={5}
        maxLength={maxLength}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </>
  );
}
