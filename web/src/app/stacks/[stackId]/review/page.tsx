import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { nextRoundText } from "@/components/DailyReviewBanner";
import { ReviewRoundFlow } from "@/components/ReviewRoundFlow";
import { api, type DailyReviewDetail } from "@/lib/api";
import { answerReviewQuestion } from "./actions";

/**
 * Today's Daily Review: the Review Round waiting to be answered (Round 1, 2 or 3), one Question
 * at a time. The API opens rounds on the Learner's requests, so this page only reads them. With
 * no round waiting it says why: when the next round opens, today's rounds are done, or nothing
 * is owed today.
 */
export default async function DailyReviewPage({ params }: PageProps<"/stacks/[stackId]/review">) {
  await connection();
  const { stackId } = await params;
  const review = await api<DailyReviewDetail>(`/stacks/${encodeURIComponent(stackId)}/review`);
  if (!review) notFound();
  const current = review.current;
  const latest = review.rounds.at(-1);

  return (
    <main>
      <p className="crumbs">
        <Link href={`/stacks/${stackId}`}>Syllabus</Link>
      </p>
      <h1>{current ? `Review Round ${current.number}` : "Daily Review"}</h1>
      {current ? (
        <>
          <p className="muted">
            {current.state === "pending"
              ? "This round is pending: your next Lesson unlocks once it's finished."
              : "Missed Questions first, then Questions from your Completed Lessons."}
          </p>
          <ReviewRoundFlow
            round={current}
            stackId={stackId}
            answerAction={answerReviewQuestion.bind(null, stackId, current.id)}
          />
        </>
      ) : (
        <p role="status" className="notice">
          {latest
            ? nextRoundText(review, latest.number)
            : "No Daily Review today. One opens each day you start with a Completed Lesson."}
        </p>
      )}
    </main>
  );
}
