import type { Answer } from "./api";

/**
 * Whether an answer has been given: a picked choice, at least one tick (multiple select), or a
 * written answer that isn't blank.
 */
export function isAnswered(answer: Answer | undefined): boolean {
  if (answer === null || answer === undefined) return false;
  if (Array.isArray(answer)) return answer.length > 0;
  return answer.trim() !== "";
}

/** The answer as it is sent: null when it isn't answered (no ticks, or a blank written one). */
export function submittedAnswer(answer: Answer | undefined): Answer {
  return answer !== undefined && isAnswered(answer) ? answer : null;
}

/** The ticks after ticking or unticking `choiceId`, kept in the order of `choiceIds`. */
export function toggleChoice(ticked: string[], choiceId: string, choiceIds: string[]): string[] {
  const next = ticked.includes(choiceId)
    ? ticked.filter((id) => id !== choiceId)
    : [...ticked, choiceId];
  return choiceIds.filter((id) => next.includes(id));
}
