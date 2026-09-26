"use server";

import {
  ApiError,
  apiPost,
  type GradingFailed,
  type LessonQuizResult,
  type QuizAnswers,
} from "@/lib/api";

/**
 * Submit a Lesson Quiz's answers. The API scores them, grading written ones; a pass completes
 * the Lesson. When grading fails this resolves to the API's `grading_failed` detail instead of
 * throwing (a thrown error loses its detail on the way to the browser), so the quiz can offer
 * to submit again. Any other refusal throws.
 */
export async function submitLessonQuiz(
  stackId: string,
  lessonId: string,
  attemptId: string,
  answers: QuizAnswers,
): Promise<LessonQuizResult | GradingFailed> {
  const lesson = `/stacks/${encodeURIComponent(stackId)}/lessons/${encodeURIComponent(lessonId)}`;
  try {
    return await apiPost<LessonQuizResult>(
      `${lesson}/quiz/${encodeURIComponent(attemptId)}/answers`,
      { answers },
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 503 && isGradingFailed(error.detail)) {
      return { code: "grading_failed", message: error.detail.message };
    }
    throw error;
  }
}

function isGradingFailed(detail: unknown): detail is GradingFailed {
  return (
    typeof detail === "object" &&
    detail !== null &&
    (detail as { code?: unknown }).code === "grading_failed" &&
    typeof (detail as { message?: unknown }).message === "string"
  );
}
