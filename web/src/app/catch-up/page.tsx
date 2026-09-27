import Link from "next/link";
import { connection } from "next/server";
import { ArchiveLine } from "@/components/ArchiveLine";
import { Notice } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { api, type CatchUp } from "@/lib/api";

/**
 * Catch-up: the past Daily Challenges the Learner hasn't played, across their Active Stacks,
 * with a count per Stack, newest first. Working through it is optional and never blocks
 * anything; a play from here is scored but doesn't count toward a Streak.
 */
export default async function CatchUpPage() {
  await connection();
  const catchUp = await api<CatchUp>("/catch-up");
  const stacks = catchUp?.stacks ?? [];
  const total = stacks.reduce((sum, s) => sum + s.count, 0);

  return (
    <main className="mx-auto max-w-3xl">
      <PageHeader
        crumbs={<Link href="/">Your Stacks</Link>}
        title="Catch-up"
        description={
          <p>
            Past Challenges you haven&apos;t played. Optional: they&apos;re scored, but
            don&apos;t count toward your Streak.
          </p>
        }
      />
      {total === 0 && (
        <Notice tone="success" role="status">
          You&apos;re all caught up.
        </Notice>
      )}
      {stacks
        .filter((s) => s.count > 0)
        .map((s) => (
          <section
            key={s.stack_id}
            aria-labelledby={`catch-up-${s.stack_id}`}
            className="mt-8 space-y-3"
          >
            <h2
              id={`catch-up-${s.stack_id}`}
              className="flex items-center gap-2 font-heading text-lg font-semibold tracking-tight"
            >
              {s.stack_name}{" "}
              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
                ({s.count})
              </span>
            </h2>
            <ul className="grid gap-2">
              {s.challenges.map((c) => (
                <li key={c.number}>
                  <ArchiveLine stackId={s.stack_id} challenge={c} />
                </li>
              ))}
            </ul>
          </section>
        ))}
    </main>
  );
}
