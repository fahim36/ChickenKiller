import Link from "next/link";
import { ArrowLeft, ArrowRight, BookOpen, CheckCircle2 } from "lucide-react";
import { LessonStateBadge } from "@/components/LessonStateBadge";
import { Inline } from "@/components/Inline";
import { formatMinutes } from "@/lib/format";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { api, type Syllabus } from "@/lib/api";
import { PlacementEntry } from "@/app/placements/PlacementEntry";
import type { PlacementEligibility } from "@/app/placements/types";

export default async function WeekPage({
  params,
}: PageProps<"/stacks/[stackId]/weeks/[weekId]">) {
  await connection();
  const { stackId, weekId } = await params;
  const syllabus = await api<Syllabus>(
    `/stacks/${encodeURIComponent(stackId)}`,
  );
  const week = syllabus?.weeks.find((w) => w.id === weekId);
  if (!week) notFound();
  const completed = week.lessons.filter(
    (lesson) => lesson.state === "completed" || lesson.state === "updated",
  ).length;
  const eligibility = await api<PlacementEligibility>(
    `/stacks/${encodeURIComponent(stackId)}/weeks/${encodeURIComponent(weekId)}/placement`,
  );
  return (
    <main className="mx-auto max-w-5xl space-y-8">
      <Link
        className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground"
        href={`/stacks/${encodeURIComponent(stackId)}`}
      >
        <ArrowLeft aria-hidden className="size-4" />
        Week map
      </Link>
      <header className="space-y-4">
        <p className="text-xs font-semibold uppercase tracking-widest text-primary">
          {syllabus?.name} · Week {week.number}
        </p>
        <h1 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
          {week.title}
        </h1>
        <p className="max-w-3xl text-base leading-relaxed text-muted-foreground">
          {week.goal}
        </p>
        <p className="inline-flex items-center gap-2 rounded-full border bg-card px-3 py-1.5 text-sm">
          <BookOpen aria-hidden className="size-4 text-primary" />
          {completed} of {week.lessons.length} Lessons complete
        </p>
      </header>
      <div className="grid items-start gap-6 lg:grid-cols-3">
        <section className="space-y-4 lg:col-span-2">
          <h2 className="font-heading text-xl font-semibold">
            Your learning path
          </h2>
          <ul className="space-y-3">
            {week.lessons.map((lesson) => (
              <li
                key={lesson.id}
                className="rounded-2xl border bg-card p-5 shadow-xs"
              >
                <div className="mb-3 flex items-center justify-between gap-3">
                  <LessonStateBadge state={lesson.state} />
                  <span className="text-xs text-muted-foreground">
                    {formatMinutes(lesson.minutes)}
                  </span>
                </div>
                <Link
                  className="group flex items-center justify-between gap-3 text-base font-semibold hover:text-primary"
                  href={`/stacks/${encodeURIComponent(stackId)}/lessons/${encodeURIComponent(lesson.id)}`}
                >
                  <Inline text={lesson.title} />
                  <ArrowRight
                    aria-hidden
                    className="size-4 shrink-0 text-muted-foreground"
                  />
                </Link>{" "}
                {lesson.placement_attempt_id && (
                  <>
                    {" "}
                    <Link
                      className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-success-foreground underline underline-offset-4"
                      href={`/placements/${lesson.placement_attempt_id}`}
                    >
                      <CheckCircle2 aria-hidden className="size-3.5" />
                      Completed by placement
                    </Link>
                  </>
                )}
              </li>
            ))}
          </ul>
        </section>
        <aside className="lg:sticky lg:top-6">
          {eligibility ? (
            <PlacementEntry
              stack={stackId}
              week={weekId}
              eligibility={eligibility}
              enabled={process.env.PLACEMENT_ENABLED === "true"}
            />
          ) : (
            <p role="alert">Placement eligibility could not be loaded.</p>
          )}
        </aside>
      </div>
    </main>
  );
}
