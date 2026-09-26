import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { LessonQuiz } from "@/components/LessonQuiz";
import { RetakeFlow } from "@/components/RetakeFlow";
import { api, ApiError, apiPost, type LessonQuiz as Quiz, type Retakes } from "@/lib/api";
import { answerRetake, submitLessonQuiz } from "./actions";

/**
 * The Lesson Quiz. Opening the page starts the quiz, or resumes the one the Learner started and
 * hasn't submitted, so a reload shows the same Questions. If the last quiz passed with Missed
 * Questions, the page shows their pending Retakes instead. The API refuses a Lesson that isn't
 * the Learner's Unlocked Lesson, and this page says why.
 */
export default async function LessonQuizPage({
  params,
}: PageProps<"/stacks/[stackId]/lessons/[lessonId]/quiz">) {
  await connection();
  const { stackId, lessonId } = await params;
  const lessonUrl = `/stacks/${encodeURIComponent(stackId)}/lessons/${encodeURIComponent(lessonId)}`;
  const crumbs = (
    <p className="crumbs">
      <Link href={`/stacks/${stackId}`}>Syllabus</Link> / <Link href={lessonUrl}>Lesson</Link>
    </p>
  );

  let quiz: Quiz;
  try {
    quiz = await apiPost<Quiz>(`${lessonUrl}/quiz`, undefined);
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    if (error.status === 404) notFound();
    if (error.status !== 409) throw error;
    const attemptId = pendingRetakesAttempt(error.detail);
    const pending = attemptId
      ? await api<Retakes>(`${lessonUrl}/quiz/${encodeURIComponent(attemptId)}/retakes`)
      : null;
    if (pending && pending.retakes.length > 0) {
      return (
        <main>
          {crumbs}
          <h1>Retakes</h1>
          <p className="muted">
            You passed this Lesson&apos;s quiz. Retake each Missed Question to complete it.
          </p>
          <RetakeFlow
            retakes={pending.retakes}
            stackId={stackId}
            answerAction={answerRetake.bind(null, stackId, lessonId)}
          />
        </main>
      );
    }
    return (
      <main>
        <h1>Lesson Quiz</h1>
        <p role="alert" className="notice notice-error">
          {pending?.lesson_completed
            ? "You've already completed this Lesson."
            : refusalMessage(error.detail)}
        </p>
        <p>
          <Link href={lessonUrl}>Back to the Lesson</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      {crumbs}
      <h1>Lesson Quiz</h1>
      <p className="muted">
        {quiz.questions.length} Questions. The Pass Mark is {quiz.pass_mark}%; an unanswered
        Question counts as missed.
      </p>
      <LessonQuiz
        quiz={quiz}
        stackId={stackId}
        submitAction={submitLessonQuiz.bind(null, stackId, lessonId, quiz.attempt_id)}
        answerRetakeAction={answerRetake.bind(null, stackId, lessonId)}
      />
    </main>
  );
}

/** The passed attempt whose Retakes are pending, from a 409 `retakes_pending`. */
function pendingRetakesAttempt(detail: unknown): string | null {
  if (typeof detail !== "object" || detail === null) return null;
  const { code, attempt_id } = detail as { code?: unknown; attempt_id?: unknown };
  return code === "retakes_pending" && typeof attempt_id === "string" ? attempt_id : null;
}

function refusalMessage(detail: unknown): string {
  if (typeof detail === "object" && detail !== null && "message" in detail) {
    return String(detail.message);
  }
  return "This Lesson Quiz can't be started right now.";
}
