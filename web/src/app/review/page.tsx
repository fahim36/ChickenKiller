import Link from "next/link";
import { connection } from "next/server";
import { Notice } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { ReviewFlow } from "@/components/ReviewFlow";
import { api, type ReviewSet } from "@/lib/api";
import { answerReviewQuestion } from "./actions";

/**
 * Review: a set of up to ten Questions across all the Learner's Active Stacks, answered one at
 * a time. Missed Questions come first, then Questions from Completed Lessons. It is optional,
 * has no rounds or timers, and never locks anything. Each load draws a fresh set; with nothing
 * due, the page says so.
 */
export default async function ReviewPage() {
  await connection();
  const reviewSet = await api<ReviewSet>("/review");
  const questions = reviewSet?.questions ?? [];

  return (
    <main className="mx-auto max-w-3xl">
      <PageHeader
        crumbs={<Link href="/">Your Stacks</Link>}
        title="Review"
        description={
          reviewSet &&
          questions.length > 0 && (
            <p>
              Optional: practise whenever you like. Missed Questions come first, then Questions
              from your Completed Lessons.
            </p>
          )
        }
      />
      {reviewSet && questions.length > 0 ? (
        <ReviewFlow reviewSet={reviewSet} answerAction={answerReviewQuestion} />
      ) : (
        <Notice role="status">
          Nothing to review right now. Missed Questions and Questions from your Completed Lessons
          come back here.
        </Notice>
      )}
    </main>
  );
}
