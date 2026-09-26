import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { DailyReviewBanner } from "@/components/DailyReviewBanner";
import { Inline } from "@/components/Inline";
import { LessonStateBadge } from "@/components/LessonStateBadge";
import { MilestoneChecklist } from "@/components/MilestoneChecklist";
import { api, type Syllabus } from "@/lib/api";
import { formatMinutes, weekMinutes } from "@/lib/format";
import { setMilestoneTicked } from "./actions";

/**
 * The Week map: the Active Stack's Weeks in Syllabus order, each with its Lessons (Completed,
 * Unlocked or Locked) and its Milestone checklist. Every Lesson links to its page, so a Learner
 * can read ahead; only the quiz is locked, and the API enforces that. The Learner's Streak and
 * today's Daily Review sit on top; while its round is pending, the Lesson it locks says so.
 */
export default async function WeekMapPage({ params }: PageProps<"/stacks/[stackId]">) {
  await connection();
  const { stackId } = await params;
  const syllabus = await api<Syllabus>(`/stacks/${encodeURIComponent(stackId)}`);
  if (!syllabus) notFound();
  const tickAction = setMilestoneTicked.bind(null, syllabus.id);

  return (
    <main>
      <p className="crumbs">
        <Link href="/settings">Switch Stack</Link>
      </p>
      <h1>{syllabus.name}</h1>
      <p className="muted">
        {syllabus.summary} · Syllabus {syllabus.version}
      </p>
      <p role="status" aria-label="Streak">
        <strong>Streak:</strong> {syllabus.streak} {syllabus.streak === 1 ? "day" : "days"}
      </p>
      {syllabus.daily_review && (
        <DailyReviewBanner review={syllabus.daily_review} stackId={syllabus.id} now={new Date()} />
      )}

      {syllabus.weeks.map((week) => (
        <section key={week.id} className="week" aria-labelledby={`week-${week.id}`}>
          <h2 id={`week-${week.id}`}>
            Week {week.number}: {week.title}{" "}
            <span className="muted small">{formatMinutes(weekMinutes(week))}</span>
          </h2>
          <p>{week.goal}</p>
          <ol className="lessons" aria-label="Lessons">
            {week.lessons.map((lesson) => (
              <li key={lesson.id} className={`lesson-${lesson.state}`}>
                <LessonStateBadge state={lesson.state} />{" "}
                <Link href={`/stacks/${syllabus.id}/lessons/${lesson.id}`}>
                  <Inline text={lesson.title} />
                </Link>
                {lesson.waiting_for_review && (
                  <span className="small muted"> · Finish your Review Round to unlock</span>
                )}
              </li>
            ))}
          </ol>
          {week.milestones.length > 0 && (
            <MilestoneChecklist milestones={week.milestones} tickAction={tickAction} />
          )}
          <p className="small">
            <strong>Deliverable:</strong> {week.deliverable}
          </p>
        </section>
      ))}
    </main>
  );
}
