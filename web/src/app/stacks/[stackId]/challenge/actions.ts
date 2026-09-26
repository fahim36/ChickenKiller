"use server";

import { apiPostGraded, type ChallengeAnswerResult, type GradingFailed } from "@/lib/api";

/**
 * Answer one Question of Daily Challenge #`number` on the Stack: a choice ID, a written answer,
 * or null. The API scores only the first answer to each Question. Resolves to `grading_failed`
 * when an answer that doesn't count can't be graded (a first answer that can't be graded comes
 * back as "ungraded" instead).
 */
export async function answerChallengeQuestion(
  stackId: string,
  number: number,
  questionId: string,
  answer: string | null,
): Promise<ChallengeAnswerResult | GradingFailed> {
  return apiPostGraded<ChallengeAnswerResult>(
    `/stacks/${encodeURIComponent(stackId)}/challenges/${number}/answers`,
    { question_id: questionId, answer },
  );
}
