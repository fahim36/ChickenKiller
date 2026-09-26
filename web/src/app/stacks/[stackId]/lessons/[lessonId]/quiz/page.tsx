import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { LessonQuiz } from "@/components/LessonQuiz";
import { ApiError, apiPost, type LessonQuiz as Quiz } from "@/lib/api";
import { submitLessonQuiz } from "./actions";

/**
 * The Lesson Quiz. Opening the page starts the quiz, or resumes the one the Learner started and
 * hasn't submitted, so a reload shows the same Questions. The API refuses a Lesson that isn't
 * the Learner's Unlocked Lesson, and this page says why.
 */
export default async function LessonQuizPage({
  params,
}: PageProps<"/stacks/[stackId]/lessons/[lessonId]/quiz">) {
  await connection();
  const { stackId, lessonId } = await params;
  const lessonUrl = `/stacks/${encodeURIComponent(stackId)}/lessons/${encodeURIComponent(lessonId)}`;

  let quiz: Quiz;
  try {
    quiz = await apiPost<Quiz>(`${lessonUrl}/quiz`, undefined);
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    if (error.status === 404) notFound();
    if (error.status !== 409) throw error;
    return (
      <main>
        <h1>Lesson Quiz</h1>
        <p role="alert" className="notice notice-error">
          {refusalMessage(error.detail)}
        </p>
        <p>
          <Link href={lessonUrl}>Back to the Lesson</Link>
        </p>
      </main>
    );
  }

  return (
    <main>
      <p className="crumbs">
        <Link href={`/stacks/${stackId}`}>Syllabus</Link> /{" "}
        <Link href={lessonUrl}>Lesson</Link>
      </p>
      <h1>Lesson Quiz</h1>
      <p className="muted">
        {quiz.questions.length} Questions. The Pass Mark is {quiz.pass_mark}%; an unanswered
        Question counts as missed.
      </p>
      <LessonQuiz
        quiz={quiz}
        stackId={stackId}
        submitAction={submitLessonQuiz.bind(null, stackId, lessonId, quiz.attempt_id)}
      />
    </main>
  );
}

function refusalMessage(detail: unknown): string {
  if (typeof detail === "object" && detail !== null && "message" in detail) {
    return String(detail.message);
  }
  return "This Lesson Quiz can't be started right now.";
}
