"use server";

import {
  ApiError,
  apiPost,
  type GradingFailed,
  type LessonQuizResult,
  type QuizAnswers,
  type RetakeResult,
} from "@/lib/api";

function lessonPath(stackId: string, lessonId: string): string {
  return `/stacks/${encodeURIComponent(stackId)}/lessons/${encodeURIComponent(lessonId)}`;
}

/**
 * POST to the API, resolving to the `grading_failed` detail instead of throwing when written
 * answers couldn't be graded (a thrown error loses its detail on the way to the browser), so
 * the page can offer to submit again. Any other refusal throws.
 */
async function postGraded<T>(path: string, body: unknown): Promise<T | GradingFailed> {
  try {
    return await apiPost<T>(path, body);
  } catch (error) {
    if (error instanceof ApiError && error.status === 503 && isGradingFailed(error.detail)) {
      return { code: "grading_failed", message: error.detail.message };
    }
    throw error;
  }
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
  return postGraded<LessonQuizResult>(`${lesson}/quiz/${encodeURIComponent(attemptId)}/answers`, {
    answers,
  });
}

/**
 * Answer a Retake's sibling Question: a choice ID, a written answer, or null for unanswered.
 * Resolves to `grading_failed` when a written answer can't be graded.
 */
export async function answerRetake(
  stackId: string,
  lessonId: string,
  retakeId: string,
  answer: string | null,
): Promise<RetakeResult | GradingFailed> {
  const lesson = lessonPath(stackId, lessonId);
  return postGraded<RetakeResult>(`${lesson}/retakes/${encodeURIComponent(retakeId)}/answers`, {
    answer,
  });
}

function isGradingFailed(detail: unknown): detail is GradingFailed {
  return (
    typeof detail === "object" &&
    detail !== null &&
    (detail as { code?: unknown }).code === "grading_failed" &&
    typeof (detail as { message?: unknown }).message === "string"
  );
}
