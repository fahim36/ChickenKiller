"use client";

import { Textarea } from "@/components/ui/textarea";
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
    <div className="space-y-2">
      <label htmlFor={id} className="text-sm font-medium text-muted-foreground">
        Your answer
      </label>
      <Textarea
        id={id}
        name={question.id}
        rows={5}
        maxLength={maxLength}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="min-h-32 resize-y bg-background text-base leading-relaxed"
        placeholder="Explain it the way you would in an interview…"
      />
      <p aria-hidden className="text-right text-xs text-muted-foreground tabular-nums">
        {value.length} / {maxLength}
      </p>
    </div>
  );
}
