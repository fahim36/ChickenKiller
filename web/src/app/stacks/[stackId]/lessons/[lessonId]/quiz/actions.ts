"use server";

import {
  apiPost,
  type LessonQuizResult,
  type QuizAnswers,
  type RetakeResult,
} from "@/lib/api";

function lessonPath(stackId: string, lessonId: string): string {
  return `/stacks/${encodeURIComponent(stackId)}/lessons/${encodeURIComponent(lessonId)}`;
}

/**
 * Submit a Lesson Quiz's answers. The API scores them; a pass with no Missed Question completes
 * the Lesson, a pass with Missed Questions opens their Retakes.
 */
export async function submitLessonQuiz(
  stackId: string,
  lessonId: string,
  attemptId: string,
  answers: QuizAnswers,
): Promise<LessonQuizResult> {
  const lesson = lessonPath(stackId, lessonId);
  return apiPost<LessonQuizResult>(`${lesson}/quiz/${encodeURIComponent(attemptId)}/answers`, {
    answers,
  });
}

/** Answer a Retake's sibling Question (a choice ID, or null for unanswered). */
export async function answerRetake(
  stackId: string,
  lessonId: string,
  retakeId: string,
  answer: string | null,
): Promise<RetakeResult> {
  const lesson = lessonPath(stackId, lessonId);
  return apiPost<RetakeResult>(`${lesson}/retakes/${encodeURIComponent(retakeId)}/answers`, {
    answer,
  });
}
