import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { DailyChallengeFlow } from "@/components/DailyChallengeFlow";
import { PageHeader } from "@/components/PageHeader";
import { api, type StackChallenge } from "@/lib/api";
import { answerChallengeQuestion } from "../../challenge/actions";

/**
 * One Daily Challenge from a Stack's Archive, played exactly like today's: only the first try
 * is scored, misses become Missed Questions, and once finished it shows that first result and
 * can be replayed for learning. A past Challenge's play never counts toward a Streak; today's,
 * opened from here, is the same as from home. Retired Questions show why, and can't be answered.
 */
export default async function ArchivedChallengePage({
  params,
}: PageProps<"/stacks/[stackId]/archive/[number]">) {
  await connection();
  const { stackId, number } = await params;
  if (!/^[1-9]\d*$/.test(number)) notFound();
  const found = await api<StackChallenge>(
    `/stacks/${encodeURIComponent(stackId)}/challenges/${number}`,
  );
  if (!found) notFound();
  const { challenge } = found;
  const past = challenge.day !== found.day;

  return (
    <main className="mx-auto max-w-3xl">
      <PageHeader
        crumbs={
          <>
            <Link href="/">Your Stacks</Link> ·{" "}
            <Link href={`/stacks/${encodeURIComponent(stackId)}/archive`}>Archive</Link>
          </>
        }
        title={challenge.label}
        description={
          past &&
          challenge.status !== "finished" && (
            <p>From the Archive: scored as usual, but it doesn&apos;t count toward your Streak.</p>
          )
        }
      />
      <DailyChallengeFlow
        key={challenge.number}
        stackId={stackId}
        challenge={challenge}
        answerAction={answerChallengeQuestion.bind(null, stackId, challenge.number)}
      />
    </main>
  );
}
