import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { DailyChallengeFlow } from "@/components/DailyChallengeFlow";
import { Notice } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { api, type TodaysChallenge } from "@/lib/api";
import { answerChallengeQuestion } from "./actions";

/**
 * Today's Daily Challenge on one Active Stack: the one dated today (UTC), released at 00:00
 * UTC, the same three Questions for everyone. The page picks up where the Learner left off:
 * the next Question not answered yet, or the score once finished, with a replay for learning.
 * A Day with no Challenge written says so.
 */
export default async function ChallengePage({ params }: PageProps<"/stacks/[stackId]/challenge">) {
  await connection();
  const { stackId } = await params;
  const today = await api<TodaysChallenge>(
    `/stacks/${encodeURIComponent(stackId)}/challenges/today`,
  );
  if (!today) notFound();
  const challenge = today.challenge;

  return (
    <main className="mx-auto max-w-3xl">
      <PageHeader
        crumbs={<Link href="/">Your Stacks</Link>}
        title={challenge ? challenge.label : `${today.stack_name}: Daily Challenge`}
      />
      {challenge ? (
        <DailyChallengeFlow
          stackId={stackId}
          challenge={challenge}
          answerAction={answerChallengeQuestion.bind(null, stackId, challenge.number)}
        />
      ) : (
        <Notice role="status">No Challenge today. The next one is released at 00:00 UTC.</Notice>
      )}
    </main>
  );
}
