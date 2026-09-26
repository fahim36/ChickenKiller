import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Inline } from "@/components/Inline";
import { LessonStateBadge } from "@/components/LessonStateBadge";
import { MaterialList } from "@/components/MaterialList";
import { api, type Lesson } from "@/lib/api";
import { formatMinutes } from "@/lib/format";

export default async function LessonPage({
  params,
}: PageProps<"/stacks/[stackId]/lessons/[lessonId]">) {
  await connection();
  const { stackId, lessonId } = await params;
  const lesson = await api<Lesson>(
    `/stacks/${encodeURIComponent(stackId)}/lessons/${encodeURIComponent(lessonId)}`,
  );
  if (!lesson) notFound();

  return (
    <main>
      <p className="crumbs">
        <Link href={`/stacks/${lesson.stack_id}`}>Syllabus</Link> /
        Week {lesson.week.number}: {lesson.week.title}
      </p>
      <h1>
        <Inline text={lesson.title} />
      </h1>
      <p className="muted">
        <LessonStateBadge state={lesson.state} /> {formatMinutes(lesson.minutes)}
      </p>
      {lesson.state === "unlocked" && (
        <p>
          <Link
            className="button"
            href={`/stacks/${lesson.stack_id}/lessons/${lesson.id}/quiz`}
            prefetch={false}
          >
            Start the Lesson Quiz
          </Link>{" "}
          <span className="small muted">Take it now, or after studying the Materials.</span>
        </p>
      )}
      {lesson.waiting_for_review && (
        <p role="note" className="small">
          Finish your <Link href={`/stacks/${lesson.stack_id}/review`}>Review Round</Link> to
          unlock this Lesson&apos;s quiz.
        </p>
      )}
      {lesson.state === "locked" && !lesson.waiting_for_review && (
        <p role="note" className="small">
          You can read ahead. The Lesson Quiz opens once you&apos;ve completed the Lessons before
          this one.
        </p>
      )}

      <h2>Topics</h2>
      <ul>
        {lesson.topics.map((t) => (
          <li key={t}>
            <Inline text={t} />
          </li>
        ))}
      </ul>

      {lesson.exercise && (
        <>
          <h2>Exercise</h2>
          <p>
            <Inline text={lesson.exercise} />
          </p>
        </>
      )}

      <h2>Materials</h2>
      <MaterialList materials={lesson.materials} />

      <nav className="pager">
        {lesson.previous_lesson_id ? (
          <Link href={`/stacks/${lesson.stack_id}/lessons/${lesson.previous_lesson_id}`}>
            ← Previous Lesson
          </Link>
        ) : (
          <span />
        )}
        {lesson.next_lesson_id && (
          <Link href={`/stacks/${lesson.stack_id}/lessons/${lesson.next_lesson_id}`}>
            Next Lesson →
          </Link>
        )}
      </nav>
    </main>
  );
}
