import Link from "next/link";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import { api, type Me, type TodaysChallenge } from "@/lib/api";

/**
 * Home: one card per Active Stack, with today's Daily Challenge (Play, Continue, or the score
 * and a Replay) and a link to its Week map, and a link to Review, which spans every Active
 * Stack. A first sign-in has no Active Stack yet, so it goes to onboarding. Each Stack's card
 * is its own section, for what later belongs to one Stack (its Streak, #18).
 */
export default async function Home() {
  await connection();
  const me = await api<Me>("/me");
  if (!me || me.needs_onboarding) redirect("/onboarding");
  const todays = await Promise.all(
    me.active_stacks.map((stack) =>
      api<TodaysChallenge>(`/stacks/${encodeURIComponent(stack.id)}/challenges/today`),
    ),
  );

  return (
    <main>
      <h1>Your Stacks</h1>
      <ul className="cards">
        {me.active_stacks.map((stack, i) => (
          <li key={stack.id}>
            <section className="card" aria-labelledby={`stack-${stack.id}`}>
              <h2 id={`stack-${stack.id}`}>{stack.name}</h2>
              <TodaysChallengeLine stackId={stack.id} today={todays[i]} />
              <p>
                <Link href={`/stacks/${encodeURIComponent(stack.id)}`}>Week map</Link>
              </p>
            </section>
          </li>
        ))}
      </ul>
      <p>
        <Link href="/review">Review</Link>{" "}
        <span className="small muted">
          Practise Missed Questions and past Lessons from all your Stacks, whenever you like.
        </span>
      </p>
      <p className="small">
        <Link href="/settings">Add or drop Stacks</Link>
      </p>
    </main>
  );
}

/** A Stack's Daily Challenge for today (UTC): Play, Continue, or "Played: 2/3 · Replay". */
function TodaysChallengeLine({
  stackId,
  today,
}: {
  stackId: string;
  today: TodaysChallenge | null;
}) {
  const challenge = today?.challenge;
  if (!challenge) return <p className="muted">No Challenge today</p>;
  const href = `/stacks/${encodeURIComponent(stackId)}/challenge`;
  return (
    <p>
      <strong>{challenge.label}</strong>{" "}
      {challenge.status === "finished" ? (
        <>
          <span>
            Played: {challenge.score}/{challenge.out_of}
          </span>{" "}
          · <Link href={href}>Replay</Link>
        </>
      ) : (
        <Link className="button" href={href}>
          {challenge.status === "in_progress" ? "Continue" : "Play"}
        </Link>
      )}
    </p>
  );
}
