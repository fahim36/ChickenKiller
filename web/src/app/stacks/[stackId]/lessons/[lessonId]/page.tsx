import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Inline } from "@/components/Inline";
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
        <Link href="/">Stacks</Link> / <Link href={`/stacks/${lesson.stack_id}`}>Syllabus</Link> /
        Week {lesson.week.number}: {lesson.week.title}
      </p>
      <h1>
        <Inline text={lesson.title} />
      </h1>
      <p className="muted">{formatMinutes(lesson.minutes)}</p>

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
