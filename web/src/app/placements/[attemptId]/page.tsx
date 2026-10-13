import { notFound } from "next/navigation";
import { connection } from "next/server";
import { api, type Syllabus } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { PlacementPractice } from "../PlacementPractice";
import type { PlacementAttempt } from "../types";

export default async function PlacementPage({
  params,
}: PageProps<"/placements/[attemptId]">) {
  await connection();
  const { attemptId } = await params;
  const attempt = await api<PlacementAttempt>(
    `/me/placements/${encodeURIComponent(attemptId)}`,
  );
  if (!attempt) notFound();
  const syllabus = await api<Syllabus>(
    `/stacks/${encodeURIComponent(attempt.stack_id)}`,
  );
  const week = syllabus?.weeks.find((w) => w.id === attempt.week_id);
  const lessonTitles = Object.fromEntries(
    (week?.lessons ?? []).map((lesson) => [lesson.id, lesson.title]),
  );
  return (
    <main className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="Placement Quiz"
        description={
          <p>
            {syllabus?.name ?? "Your Stack"} ·{" "}
            {week
              ? `Week ${week.number}: ${week.title}`
              : "Whole-Week self-assessment"}
          </p>
        }
      />
      <PlacementPractice initial={attempt} lessonTitles={lessonTitles} />
    </main>
  );
}
