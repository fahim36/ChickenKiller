import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { LessonQuiz } from "@/components/LessonQuiz";
import { Notice } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { RetakeFlow, RetakeNotices } from "@/components/RetakeFlow";
import { Button } from "@/components/ui/button";
import {
  api,
  ApiError,
  apiPost,
  type LessonQuiz as Quiz,
  type Retakes,
} from "@/lib/api";
import { answerRetake, submitLessonQuiz } from "./actions";

/**
 * The Lesson Quiz. Opening the page starts the quiz, or resumes the one the Learner started and
 * hasn't submitted, so a reload shows the same Questions. If the last quiz passed with Missed
 * Questions, the page shows their pending Retakes instead. The API refuses a Lesson that isn't
 * the Learner's Unlocked Lesson, and this page says why.
 */
export default async function LessonQuizPage({
  params,
  searchParams,
}: PageProps<"/stacks/[stackId]/lessons/[lessonId]/quiz">) {
  await connection();
  const { stackId, lessonId } = await params;
  const lessonUrl = `/stacks/${encodeURIComponent(stackId)}/lessons/${encodeURIComponent(lessonId)}`;
  const crumbs = (
    <>
      <Link href={`/stacks/${stackId}`}>Syllabus</Link> /{" "}
      <Link href={lessonUrl}>Lesson</Link>
    </>
  );

  const retakeView = (pending: Retakes) => (
    <main className="mx-auto max-w-3xl">
      <PageHeader
        crumbs={<Link href={`/stacks/${encodeURIComponent(stackId)}`}>Syllabus</Link>}
        title="Retakes"
        description="You passed this Lesson's quiz. Retake each Missed Question to complete it."
      />
      <RetakeFlow
        retakes={pending.retakes}
        notices={pending.notices}
        stackId={stackId}
        maxAnswerChars={pending.max_answer_chars}
        answerAction={answerRetake.bind(null, stackId, lessonId)}
      />
    </main>
  );
  const query = await (searchParams ?? Promise.resolve({}));
  const attemptId = query.attempt_id;
  if (typeof attemptId === "string" && attemptId) {
    const pending = await api<Retakes>(
      `${lessonUrl}/quiz/${encodeURIComponent(attemptId)}/retakes`,
    );
    if (pending && pending.retakes.length > 0) return retakeView(pending);
    return (
      <main>
        <PageHeader
          title="Retakes"
          crumbs={
            <Link href={`/stacks/${encodeURIComponent(stackId)}`}>
              Syllabus
            </Link>
          }
        />
        <Notice role="status">
          <RetakeNotices notices={pending?.notices} />
          {pending?.lesson_completed
            ? "These Retakes are resolved. Choose your next activity on Home."
            : "This Retake attempt couldn't be loaded. Return to Home for current guidance."}
        </Notice>
        <Link href="/">Your Stacks</Link>
      </main>
    );
  }

  let quiz: Quiz;
  try {
    quiz = await apiPost<Quiz>(`${lessonUrl}/quiz`, undefined);
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    if (error.status === 404) notFound();
    if (error.status !== 409) throw error;
    const attemptId = pendingRetakesAttempt(error.detail);
    const pending = attemptId
      ? await api<Retakes>(
          `${lessonUrl}/quiz/${encodeURIComponent(attemptId)}/retakes`,
        )
      : null;
    if (pending && pending.retakes.length > 0) {
      return retakeView(pending);
    }
    return (
      <main className="mx-auto max-w-3xl space-y-6">
        <PageHeader crumbs={crumbs} title="Lesson Quiz" className="mb-0" />
        <Notice
          tone={pending?.lesson_completed ? "success" : "error"}
          role="alert"
        >
          <RetakeNotices notices={pending?.notices} />
          {pending?.lesson_completed
            ? "You've already completed this Lesson."
            : refusalMessage(error.detail)}
        </Notice>
        <p>
          <Button asChild variant="outline">
            <Link href={lessonUrl}>
              <ArrowLeft aria-hidden />
              Back to the Lesson
            </Link>
          </Button>
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl">
      <PageHeader
        crumbs={crumbs}
        title="Lesson Quiz"
        description={
          <>
            {quiz.questions.length} Questions. The Pass Mark is {quiz.pass_mark}
            %; an unanswered Question counts as missed.
          </>
        }
      />
      <LessonQuiz
        quiz={quiz}
        stackId={stackId}
        submitAction={submitLessonQuiz.bind(
          null,
          stackId,
          lessonId,
          quiz.attempt_id,
        )}
        answerRetakeAction={answerRetake.bind(null, stackId, lessonId)}
      />
    </main>
  );
}

/** The passed attempt whose Retakes are pending, from a 409 `retakes_pending`. */
function pendingRetakesAttempt(detail: unknown): string | null {
  if (typeof detail !== "object" || detail === null) return null;
  const { code, attempt_id } = detail as {
    code?: unknown;
    attempt_id?: unknown;
  };
  return code === "retakes_pending" && typeof attempt_id === "string"
    ? attempt_id
    : null;
}

function refusalMessage(detail: unknown): string {
  if (typeof detail === "object" && detail !== null && "message" in detail) {
    return String(detail.message);
  }
  return "This Lesson Quiz can't be started right now.";
}
