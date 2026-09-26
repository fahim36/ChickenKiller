"use server";

import { apiPostGraded, type GradingFailed, type ReviewAnswerResult } from "@/lib/api";

/**
 * Answer one Question of a Review Round: a choice ID, a written answer, or null for unanswered.
 * Resolves to `grading_failed` when a written answer can't be graded.
 */
export async function answerReviewQuestion(
  stackId: string,
  roundId: string,
  questionId: string,
  answer: string | null,
): Promise<ReviewAnswerResult | GradingFailed> {
  return apiPostGraded<ReviewAnswerResult>(
    `/stacks/${encodeURIComponent(stackId)}/review/rounds/${encodeURIComponent(roundId)}/answers`,
    { question_id: questionId, answer },
  );
}
