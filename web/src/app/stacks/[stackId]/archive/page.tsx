import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { ArchiveLine } from "@/components/ArchiveLine";
import { type Archive, api } from "@/lib/api";

/**
 * A Stack's Archive: every released Daily Challenge, back to #1, newest first ("#40 · 26 Sep"),
 * each with the Learner's first score or a Play. Any of them can be played; a past Challenge's
 * play is scored and its misses recorded, but it never counts toward a Streak. An Upcoming
 * Challenge is never listed.
 */
export default async function ArchivePage({ params }: PageProps<"/stacks/[stackId]/archive">) {
  await connection();
  const { stackId } = await params;
  const archive = await api<Archive>(`/stacks/${encodeURIComponent(stackId)}/challenges`);
  if (!archive) notFound();

  return (
    <main>
      <p className="crumbs">
        <Link href="/">Your Stacks</Link>
      </p>
      <h1>{archive.stack_name}: Archive</h1>
      <p className="muted">
        Every Daily Challenge so far. A first play of a past one is scored, but only today&apos;s
        Challenge, played today, counts toward your Streak.
      </p>
      {archive.challenges.length === 0 ? (
        <p role="status" className="notice">
          No Challenges released yet.
        </p>
      ) : (
        <ul className="archive">
          {archive.challenges.map((c) => (
            <li key={c.number}>
              <ArchiveLine stackId={stackId} challenge={c} />
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
