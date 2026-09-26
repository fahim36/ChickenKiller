import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { DailyChallengeFlow } from "@/components/DailyChallengeFlow";
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
    <main>
      <p className="crumbs">
        <Link href="/">Your Stacks</Link>
      </p>
      <h1>{challenge ? challenge.label : `${today.stack_name}: Daily Challenge`}</h1>
      {challenge ? (
        <DailyChallengeFlow
          challenge={challenge}
          answerAction={answerChallengeQuestion.bind(null, stackId, challenge.number)}
        />
      ) : (
        <p role="status" className="notice">
          No Challenge today. The next one is released at 00:00 UTC.
        </p>
      )}
    </main>
  );
}
