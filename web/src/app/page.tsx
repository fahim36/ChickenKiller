import Link from "next/link";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import { api, type Me } from "@/lib/api";

/**
 * Home: one card per Active Stack, linking to its Week map, and a link to Review, which spans
 * every Active Stack. A first sign-in has no Active Stack yet, so it goes to onboarding. Each
 * Stack's card is its own section, for what later belongs to one Stack (its Daily Challenge
 * and Streak, #17 and #18).
 */
export default async function Home() {
  await connection();
  const me = await api<Me>("/me");
  if (!me || me.needs_onboarding) redirect("/onboarding");

  return (
    <main>
      <h1>Your Stacks</h1>
      <ul className="cards">
        {me.active_stacks.map((stack) => (
          <li key={stack.id}>
            <section className="card" aria-labelledby={`stack-${stack.id}`}>
              <h2 id={`stack-${stack.id}`}>{stack.name}</h2>
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
