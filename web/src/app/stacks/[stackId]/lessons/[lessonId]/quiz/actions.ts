"use server";

import { apiPost, type LessonQuizResult, type QuizAnswers } from "@/lib/api";

/** Submit a Lesson Quiz's answers. The API scores them; a pass completes the Lesson. */
export async function submitLessonQuiz(
  stackId: string,
  lessonId: string,
  attemptId: string,
  answers: QuizAnswers,
): Promise<LessonQuizResult> {
  const lesson = `/stacks/${encodeURIComponent(stackId)}/lessons/${encodeURIComponent(lessonId)}`;
  return apiPost<LessonQuizResult>(`${lesson}/quiz/${encodeURIComponent(attemptId)}/answers`, {
    answers,
  });
}
