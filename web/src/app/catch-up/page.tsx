import Link from "next/link";
import { connection } from "next/server";
import { ArchiveLine } from "@/components/ArchiveLine";
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
    <main>
      <p className="crumbs">
        <Link href="/">Your Stacks</Link>
      </p>
      <h1>Catch-up</h1>
      <p className="muted">
        Past Challenges you haven&apos;t played. Optional: they&apos;re scored, but don&apos;t count
        toward your Streak.
      </p>
      {total === 0 && (
        <p role="status" className="notice">
          You&apos;re all caught up.
        </p>
      )}
      {stacks
        .filter((s) => s.count > 0)
        .map((s) => (
          <section key={s.stack_id} aria-labelledby={`catch-up-${s.stack_id}`}>
            <h2 id={`catch-up-${s.stack_id}`}>
              {s.stack_name} <span className="muted">({s.count})</span>
            </h2>
            <ul className="archive">
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
