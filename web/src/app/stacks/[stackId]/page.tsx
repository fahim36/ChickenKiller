import {
  Clock,
  Flag,
  History,
  List,
  Network,
  Repeat,
  Target,
} from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Inline } from "@/components/Inline";
import { LessonStateBadge } from "@/components/LessonStateBadge";
import { MilestoneChecklist } from "@/components/MilestoneChecklist";
import { Crumbs } from "@/components/PageHeader";
import { api, type Syllabus } from "@/lib/api";
import { formatMinutes, weekMinutes } from "@/lib/format";
import { cn } from "@/lib/utils";
import { setMilestoneTicked } from "./actions";
import { WeekGraph } from "./WeekGraph";

/**
 * The Week map: one Active Stack's Weeks in Syllabus order, each with its Lessons (Completed,
 * Updated, Unlocked or Locked) and its Milestone checklist. Every Lesson links to its page, so a
 * Learner can read ahead; only the quiz is locked, and the API enforces that. Only completing a
 * Lesson unlocks the next: Milestone ticks and Review never change a lock. Completed Lessons a
 * Syllabus Update removed are listed last, as history: they're no longer on the path, so no
 * links. It opens as a graph; `?view=list` shows the list, where Milestones can be ticked.
 */
export default async function WeekMapPage({
  params,
  searchParams,
}: PageProps<"/stacks/[stackId]">) {
  await connection();
  const { stackId } = await params;
  const view = (await searchParams)?.view === "list" ? "list" : "graph";
  const syllabus = await api<Syllabus>(
    `/stacks/${encodeURIComponent(stackId)}`,
  );
  if (!syllabus) notFound();
  const tickAction = setMilestoneTicked.bind(null, syllabus.id);
  const lessons = syllabus.weeks.flatMap((w) => w.lessons);
  const done = lessons.filter(
    (l) => l.state === "completed" || l.state === "updated",
  ).length;
  const percent =
    lessons.length === 0 ? 0 : Math.round((done / lessons.length) * 100);

  return (
    <main className="mx-auto max-w-3xl">
      <div className="mb-8 space-y-5 rounded-3xl border bg-linear-to-br from-primary/12 via-card to-card p-6 shadow-xs sm:p-8">
        <Crumbs>
          <Link href="/">Your Stacks</Link>
        </Crumbs>
        <div className="space-y-2">
          <h1 className="font-heading text-2xl font-semibold tracking-tight sm:text-3xl">
            {syllabus.name}
          </h1>
          <p className="text-muted-foreground">
            {syllabus.summary} ·{" "}
            <span className="font-mono text-xs">
              Syllabus {syllabus.version}
            </span>
          </p>
        </div>
        <div className="space-y-2" aria-hidden>
          <div className="flex justify-between text-sm">
            <span className="font-medium">Your progress</span>
            <span className="text-muted-foreground tabular-nums">
              {done}/{lessons.length} Lessons
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary"
              style={{ width: `${percent}%` }}
            />
          </div>
        </div>
        <p className="flex items-start gap-2 text-sm text-muted-foreground">
          <Repeat aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
          <span>
            Practise your Missed Questions and past Lessons in{" "}
            <Link
              href="/review"
              className="font-medium text-foreground underline underline-offset-4 hover:text-primary"
            >
              Review
            </Link>{" "}
            whenever you like. It&apos;s optional and never locks anything.
          </span>
        </p>
      </div>

      <nav aria-label="Week map view" className="mb-6 flex justify-end">
        <div className="inline-flex rounded-xl border bg-card p-1 shadow-xs">
          <ViewLink
            href={`/stacks/${syllabus.id}`}
            active={view === "graph"}
            icon={Network}
          >
            Graph
          </ViewLink>
          <ViewLink
            href={`/stacks/${syllabus.id}?view=list`}
            active={view === "list"}
            icon={List}
          >
            List
          </ViewLink>
        </div>
      </nav>

      {view === "graph" ? (
        <WeekGraph syllabus={syllabus} />
      ) : (
        <ol className="relative space-y-6 border-l-2 border-dashed border-border pl-6 sm:pl-8">
          {syllabus.weeks.map((week) => {
            const weekDone = week.lessons.every(
              (l) => l.state === "completed" || l.state === "updated",
            );
            const current = week.lessons.some((l) => l.state === "unlocked");
            return (
              <li key={week.id} className="relative">
                <span
                  aria-hidden
                  className={cn(
                    "absolute top-6 -left-[calc(1.5rem+9px)] size-4 rounded-full border-2 border-background ring-2 sm:-left-[calc(2rem+9px)]",
                    weekDone
                      ? "bg-success ring-success/40"
                      : current
                        ? "bg-primary ring-primary/40"
                        : "bg-muted ring-border",
                  )}
                />
                <section
                  className={cn(
                    "space-y-5 rounded-2xl border bg-card p-5 shadow-xs sm:p-6",
                    current && "border-primary/40 ring-1 ring-primary/20",
                  )}
                  aria-labelledby={`week-${week.id}`}
                >
                  <div className="space-y-2">
                    <h2
                      id={`week-${week.id}`}
                      className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 font-heading text-lg font-semibold tracking-tight"
                    >
                      <span>
                        Week {week.number}: {week.title}
                      </span>{" "}
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground">
                        <Clock aria-hidden className="size-3.5" />
                        {formatMinutes(weekMinutes(week))}
                      </span>
                    </h2>
                    <p className="flex items-start gap-2 text-sm text-muted-foreground">
                      <Target aria-hidden className="mt-0.5 size-4 shrink-0" />
                      <span>{week.goal}</span>
                    </p>
                  </div>

                  <ol
                    className="divide-y overflow-hidden rounded-xl border"
                    aria-label="Lessons"
                  >
                    {week.lessons.map((lesson) => (
                      <li
                        key={lesson.id}
                        className={cn(
                          "relative flex items-center gap-3 px-3 py-2.5 transition-colors hover:bg-muted/50",
                          lesson.state === "locked" && "text-muted-foreground",
                          lesson.state === "unlocked" && "bg-accent/40",
                        )}
                      >
                        <LessonStateBadge
                          state={lesson.state}
                          className="w-26 justify-center"
                        />{" "}
                        <Link
                          href={`/stacks/${syllabus.id}/lessons/${lesson.id}`}
                          className="min-w-0 text-sm font-medium after:absolute after:inset-0 sm:text-base"
                        >
                          <Inline text={lesson.title} />
                        </Link>
                      </li>
                    ))}
                  </ol>

                  {week.milestones.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                        Milestones
                      </p>
                      <MilestoneChecklist
                        milestones={week.milestones}
                        tickAction={tickAction}
                      />
                    </div>
                  )}
                  <p className="flex items-start gap-2 rounded-xl bg-muted/60 px-3 py-2 text-sm">
                    <Flag
                      aria-hidden
                      className="mt-0.5 size-4 shrink-0 text-primary"
                    />
                    <span>
                      <strong>Deliverable:</strong> {week.deliverable}
                    </span>
                  </p>
                </section>
              </li>
            );
          })}
        </ol>
      )}

      {syllabus.removed_lessons.length > 0 && (
        <section
          className="mt-10 space-y-3 rounded-2xl border border-dashed p-5"
          aria-labelledby="removed-lessons"
        >
          <h2
            id="removed-lessons"
            className="flex items-center gap-2 font-heading text-base font-semibold text-muted-foreground"
          >
            <History aria-hidden className="size-4" />
            Completed, no longer in the Syllabus
          </h2>
          <ul className="space-y-1 text-sm">
            {syllabus.removed_lessons.map((lesson) => (
              <li key={lesson.id}>
                <Inline text={lesson.title} />
                <span className="text-muted-foreground">
                  {" "}
                  · Syllabus {lesson.version}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}

function ViewLink({
  href,
  active,
  icon: Icon,
  children,
}: {
  href: string;
  active: boolean;
  icon: typeof List;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
        active
          ? "bg-primary text-primary-foreground shadow-xs"
          : "text-muted-foreground hover:bg-muted hover:text-foreground",
      )}
    >
      <Icon aria-hidden className="size-4" />
      {children}
    </Link>
  );
}
