import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { api, type Me } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";

export interface PlacementCoverage {
  id: string;
  name: string;
  weeks: {
    id: string;
    title: string;
    status: "absent" | "gaps" | "valid";
    gaps: string[];
    plan: null | {
      version: number;
      reviewed_by: string;
      lessons: {
        lesson: string;
        count: number;
        essential_concepts: string[];
        rationale: string;
      }[];
    };
  }[];
}

export default async function PlacementCoveragePage() {
  await connection();
  const me = await api<Me>("/me");
  if (!me?.is_admin) notFound();
  const stacks = await api<PlacementCoverage[]>("/admin/placement-coverage");
  return (
    <main className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="Placement coverage"
        crumbs={<Link href="/admin/content-health">Content Health</Link>}
        description="Reviewed essential Concepts for whole-Week placement. Coverage describes content, not learner mastery."
      />
      {stacks === null ? (
        <p role="alert">
          Placement coverage could not be loaded. Try again later.
        </p>
      ) : stacks.length === 0 ? (
        <p>No imported Stacks.</p>
      ) : (
        stacks.map((stack) => (
          <section key={stack.id} className="space-y-4">
            <h2 className="text-xl font-semibold">{stack.name}</h2>
            {stack.weeks.map((week) => (
              <section key={week.id} className="rounded border p-4">
                <h3 className="font-semibold">{week.title}</h3>
                <p>
                  {week.status === "valid"
                    ? "Reviewed coverage available"
                    : week.status === "absent"
                      ? "No reviewed placement plan"
                      : "Placement coverage has gaps"}
                </p>
                {week.gaps.length > 0 && (
                  <ul>
                    {week.gaps.map((gap) => (
                      <li key={gap}>{gap}</li>
                    ))}
                  </ul>
                )}
                {week.plan && (
                  <>
                    <p>
                      Reviewed by {week.plan.reviewed_by} · version{" "}
                      {week.plan.version}
                    </p>
                    <ul>
                      {week.plan.lessons.map((lesson) => (
                        <li key={lesson.lesson}>
                          {lesson.lesson}: {lesson.count} Questions ·{" "}
                          {lesson.essential_concepts.join(", ")}
                          <p>{lesson.rationale}</p>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </section>
            ))}
          </section>
        ))
      )}
    </main>
  );
}
