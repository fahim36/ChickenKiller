"use server";

import {
  type Answer,
  apiPostGraded,
  type GradingFailed,
  type LessonQuizResult,
  type QuizAnswers,
  type RetakeResult,
} from "@/lib/api";

function lessonPath(stackId: string, lessonId: string): string {
  return `/stacks/${encodeURIComponent(stackId)}/lessons/${encodeURIComponent(lessonId)}`;
}

/**
 * Submit a Lesson Quiz's answers. The API scores them, grading written ones; a pass with no
 * Missed Question completes the Lesson, a pass with Missed Questions opens their Retakes.
 * Resolves to `grading_failed` when grading fails.
 */
export async function submitLessonQuiz(
  stackId: string,
  lessonId: string,
  attemptId: string,
  answers: QuizAnswers,
): Promise<LessonQuizResult | GradingFailed> {
  const lesson = lessonPath(stackId, lessonId);
  return apiPostGraded<LessonQuizResult>(
    `${lesson}/quiz/${encodeURIComponent(attemptId)}/answers`,
    { answers },
  );
}

/**
 * Answer a Retake's sibling Question: a choice ID, the choice IDs ticked (multiple select), a
 * written answer, or null for unanswered. Resolves to `grading_failed` when a written answer
 * can't be graded.
 */
export async function answerRetake(
  stackId: string,
  lessonId: string,
  retakeId: string,
  answer: Answer,
): Promise<RetakeResult | GradingFailed> {
  const lesson = lessonPath(stackId, lessonId);
  return apiPostGraded<RetakeResult>(`${lesson}/retakes/${encodeURIComponent(retakeId)}/answers`, {
    answer,
  });
}
