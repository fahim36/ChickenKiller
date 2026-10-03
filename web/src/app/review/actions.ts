"use server";

import {
  type Answer,
  apiPostGraded,
  type GradingFailed,
  type ReviewAnswerResult,
} from "@/lib/api";

/**
 * Answer one Question of a Review set on its Stack: a choice ID, the choice IDs ticked
 * (multiple select), a written answer, or null for unanswered. Resolves to `grading_failed`
 * when a written answer can't be graded.
 */
export async function answerReviewQuestion(
  stackId: string,
  questionId: string,
  answer: Answer,
): Promise<ReviewAnswerResult | GradingFailed> {
  return apiPostGraded<ReviewAnswerResult>("/review/answers", {
    stack_id: stackId,
    question_id: questionId,
    answer,
  });
}
