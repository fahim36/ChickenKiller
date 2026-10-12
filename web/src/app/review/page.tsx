import Link from "next/link";
import { connection } from "next/server";
import { Notice } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { ReviewFlow } from "@/components/ReviewFlow";
import { api, type ReviewSet } from "@/lib/api";
import { answerReviewQuestion, answerTargetedReviewQuestion } from "./actions";
import { TargetedReviewVisit } from "./TargetedReviewVisit";

/**
 * Review: a set of up to ten Questions across all the Learner's Active Stacks, answered one at
 * a time. Missed Questions come first, then Questions from Completed Lessons. It is optional,
 * has no rounds or timers, and never locks anything. Each load draws a fresh set; with nothing
 * due, the page says so.
 */
export default async function ReviewPage({
  searchParams,
}: Partial<PageProps<"/review">>) {
  await connection();
  const query: { [key: string]: string | string[] | undefined } =
    await (searchParams ?? Promise.resolve({}));
  const stack = query.stack_id;
  const concept = query.concept_id;
  const hasTarget = stack !== undefined || concept !== undefined;
  const validTarget =
    typeof stack === "string" &&
    !!stack &&
    typeof concept === "string" &&
    !!concept;
  if (hasTarget && !validTarget) {
    return (
      <main>
        <PageHeader title="Review" />
        <Notice>
          Select a Stack and Concept together.{" "}
          <Link href="/review">Open ordinary Review</Link>.
        </Notice>
      </main>
    );
  }
  const href = validTarget
    ? `/review?stack_id=${encodeURIComponent(stack)}&concept_id=${encodeURIComponent(concept)}`
    : "/review";
  const reviewSet = await api<ReviewSet>(href);
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
              {validTarget
                ? "Optional: practise this Concept using only Questions currently due in Review."
                : "Optional: practise whenever you like. Missed Questions come first, then Questions from your Completed Lessons."}
            </p>
          )
        }
      />
      {reviewSet && questions.length > 0 ? (
        <>
          {validTarget && (
            <TargetedReviewVisit stack={stack} concept={concept} />
          )}
          <ReviewFlow
            key={href}
            reviewSet={reviewSet}
            answerAction={
              validTarget
                ? answerTargetedReviewQuestion.bind(null, concept)
                : answerReviewQuestion
            }
            nextSetHref={href}
          />
        </>
      ) : (
        <Notice role="status">
          {!reviewSet
            ? "Review couldn't be loaded. Reload the page to try again."
            : validTarget
              ? "Nothing is due for this Concept right now. You can choose another activity."
              : "Nothing to review right now. Missed Questions and Questions from your Completed Lessons come back here."}
        </Notice>
      )}
    </main>
  );
}
