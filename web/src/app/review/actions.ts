"use server";

import {
  type Answer,
  apiPostGraded,
  apiPost,
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

export async function answerTargetedReviewQuestion(
  conceptId: string,
  stackId: string,
  questionId: string,
  answer: Answer,
): Promise<ReviewAnswerResult | GradingFailed> {
  return apiPostGraded<ReviewAnswerResult>("/review/answers", {
    stack_id: stackId,
    question_id: questionId,
    answer,
    target_concept_id: conceptId,
  });
}

export async function recordTargetedReviewVisit(
  stackId: string,
  conceptId: string,
) {
  await apiPost("/review/uptake", { stack_id: stackId, concept_id: conceptId });
}
