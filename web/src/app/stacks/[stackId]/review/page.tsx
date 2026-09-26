import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { ReviewRoundFlow } from "@/components/ReviewRoundFlow";
import { api, type DailyReviewDetail } from "@/lib/api";
import { answerReviewQuestion } from "./actions";

/**
 * Today's Daily Review: the Review Round waiting to be answered, one Question at a time. The
 * API opens Round 1 on the Learner's first use of the day, so this page only reads it. With no
 * round waiting it says why: today's rounds are done, or nothing is owed today.
 */
export default async function DailyReviewPage({ params }: PageProps<"/stacks/[stackId]/review">) {
  await connection();
  const { stackId } = await params;
  const review = await api<DailyReviewDetail>(`/stacks/${encodeURIComponent(stackId)}/review`);
  if (!review) notFound();
  const current = review.current;

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
          {review.rounds.length > 0
            ? "Today's Review Round is done."
            : "No Daily Review today. One opens each day you start with a Completed Lesson."}
        </p>
      )}
    </main>
  );
}
