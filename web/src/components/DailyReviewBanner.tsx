import Link from "next/link";
import type { DailyReview } from "@/lib/api";
import { formatClock, formatTimeLeft } from "@/lib/format";

/**
 * Today's Daily Review on the Week map: the latest Review Round, whether it is optional (and
 * for how much longer), pending (it locks the next Lesson until it's finished) or done, and a
 * link to answer it. Once it's done, when the next round opens (in UTC, like every Day),
 * or that the day's Daily Review is done. `now` is when the page was rendered.
 */
export function DailyReviewBanner({
  review,
  stackId,
  now,
}: {
  review: DailyReview;
  stackId: string;
  now: Date;
}) {
  const round = review.rounds.at(-1);
  if (!round) return null;
  const left = round.total - round.answered;
  const link = (
    <Link className="button" href={`/stacks/${stackId}/review`} prefetch={false}>
      {round.answered === 0 ? "Start the Review Round" : "Continue the Review Round"}
    </Link>
  );

  return (
    <section aria-label="Daily Review" className={`daily-review daily-review-${round.state}`}>
      {round.state === "finished" ? (
        <p>{nextRoundText(review, round.number, now)}</p>
      ) : round.state === "pending" ? (
        <>
          <p>
            <strong>
              Review Round {round.number} is pending: finish it to unlock your next Lesson.
            </strong>{" "}
            {left} of {round.total} Questions left.
          </p>
          <p>{link}</p>
        </>
      ) : (
        <>
          <p>
            Review Round {round.number} is open: {left} of {round.total} Questions left.
            Optional for another {formatTimeLeft(new Date(round.pending_at), now)}; after that it
            locks your next Lesson until it&apos;s done.
          </p>
          <p>{link}</p>
        </>
      )}
    </section>
  );
}

/**
 * What follows a finished Review Round: when the next one opens (with how long until then,
 * given `now`), or that the day's Daily Review is done. Also used by the Daily Review page.
 */
export function nextRoundText(review: DailyReview, finished: number, now?: Date): string {
  if (!review.next_round_at) return "Your Daily Review is done for today.";
  const opens = new Date(review.next_round_at);
  const at = formatClock(opens);
  const wait = now ? `, in ${formatTimeLeft(opens, now)}` : "";
  return `Review Round ${finished} is done. Review Round ${finished + 1} opens at ${at}${wait}.`;
}
