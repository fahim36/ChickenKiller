"use server";

import {
  type Answer,
  apiPostGraded,
  type ChallengeAnswerResult,
  type GradingFailed,
} from "@/lib/api";

/**
 * Answer one Question of Daily Challenge #`number` on the Stack: a choice ID, the choice IDs
 * ticked (multiple select), a written answer, or null. The API scores only the first answer to
 * each Question. Resolves to `grading_failed` when an answer that doesn't count can't be graded
 * (a first answer that can't be graded comes back as "ungraded" instead).
 */
export async function answerChallengeQuestion(
  stackId: string,
  number: number,
  questionId: string,
  answer: Answer,
): Promise<ChallengeAnswerResult | GradingFailed> {
  return apiPostGraded<ChallengeAnswerResult>(
    `/stacks/${encodeURIComponent(stackId)}/challenges/${number}/answers`,
    { question_id: questionId, answer },
  );
}
