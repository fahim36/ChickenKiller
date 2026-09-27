import { Clock, Dumbbell, ListChecks, Play } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Inline } from "@/components/Inline";
import { LessonStateBadge } from "@/components/LessonStateBadge";
import { MaterialList } from "@/components/MaterialList";
import { Notice } from "@/components/Notice";
import { Crumbs, Section } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
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
    <main className="mx-auto max-w-3xl">
      <header className="mb-8 space-y-4">
        <Crumbs>
          <Link href={`/stacks/${lesson.stack_id}`}>Syllabus</Link> /
          Week {lesson.week.number}: {lesson.week.title}
        </Crumbs>
        <h1 className="font-heading text-2xl font-semibold tracking-tight text-balance sm:text-3xl">
          <Inline text={lesson.title} />
        </h1>
        <p className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <LessonStateBadge state={lesson.state} />{" "}
          <span className="inline-flex items-center gap-1">
            <Clock aria-hidden className="size-4" />
            {formatMinutes(lesson.minutes)}
          </span>
        </p>
      </header>

      {lesson.state === "unlocked" && (
        <div className="mb-8 flex flex-col gap-4 rounded-2xl border border-primary/25 bg-linear-to-r from-primary/12 to-primary/5 p-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-muted-foreground">
            Take it now, or after studying the Materials.
          </p>
          <Button asChild size="lg" className="px-4">
            <Link href={`/stacks/${lesson.stack_id}/lessons/${lesson.id}/quiz`} prefetch={false}>
              <Play aria-hidden />
              Start the Lesson Quiz
            </Link>
          </Button>
        </div>
      )}
      {lesson.state === "updated" && (
        <Notice tone="warning" role="note" className="mb-8">
          A Syllabus Update added or changed this Lesson after you&apos;d passed it. Its new
          Questions come in your Review.
        </Notice>
      )}
      {lesson.state === "locked" && (
        <Notice tone="info" role="note" className="mb-8">
          You can read ahead. The Lesson Quiz opens once you&apos;ve completed the Lessons before
          this one.
        </Notice>
      )}

      <div className="rounded-2xl border bg-card p-5 shadow-xs sm:p-6">
        <h2 className="mb-4 flex items-center gap-2 font-heading text-lg font-semibold tracking-tight">
          <ListChecks aria-hidden className="size-5 text-primary" />
          Topics
        </h2>
        <ul className="grid gap-2 sm:grid-cols-2">
          {lesson.topics.map((t) => (
            <li key={t} className="rounded-xl bg-muted/60 px-3 py-2 text-sm">
              <Inline text={t} />
            </li>
          ))}
        </ul>
      </div>

      {lesson.exercise && (
        <div className="mt-6 flex gap-4 rounded-2xl border bg-card p-5 shadow-xs sm:p-6">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-streak/15 text-streak">
            <Dumbbell aria-hidden className="size-5" />
          </span>
          <div className="space-y-1">
            <h2 className="font-heading text-lg font-semibold tracking-tight">Exercise</h2>
            <p className="text-sm leading-relaxed text-muted-foreground sm:text-base">
              <Inline text={lesson.exercise} />
            </p>
          </div>
        </div>
      )}

      <Section title="Materials">
        <MaterialList materials={lesson.materials} />
      </Section>

      <nav className="mt-12 flex justify-between gap-3 border-t pt-6">
        {lesson.previous_lesson_id ? (
          <Button asChild variant="outline">
            <Link href={`/stacks/${lesson.stack_id}/lessons/${lesson.previous_lesson_id}`}>
              ← Previous Lesson
            </Link>
          </Button>
        ) : (
          <span />
        )}
        {lesson.next_lesson_id && (
          <Button asChild variant="outline">
            <Link href={`/stacks/${lesson.stack_id}/lessons/${lesson.next_lesson_id}`}>
              Next Lesson →
            </Link>
          </Button>
        )}
      </nav>
    </main>
  );
}
