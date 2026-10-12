import Link from "next/link";
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
  const eligibility = await api<PlacementEligibility>(
    `/stacks/${encodeURIComponent(stackId)}/weeks/${encodeURIComponent(weekId)}/placement`,
  );
  return (
    <main className="mx-auto max-w-3xl space-y-6">
      <Link href={`/stacks/${encodeURIComponent(stackId)}`}>Week map</Link>
      <h1 className="text-2xl font-semibold">
        Week {week.number} · {week.title}
      </h1>
      <p>{week.goal}</p>
      <ul>
        {week.lessons.map((lesson) => (
          <li key={lesson.id}>
            <Link
              href={`/stacks/${encodeURIComponent(stackId)}/lessons/${encodeURIComponent(lesson.id)}`}
            >
              {lesson.title}
            </Link>{" "}
            · {lesson.state}
          </li>
        ))}
      </ul>
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
    </main>
  );
}
