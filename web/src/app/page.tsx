import {
  ArrowRight,
  Archive,
  CalendarDays,
  CircleAlert,
  History,
  Map as MapIcon,
  Play,
  Repeat,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { redirect, unstable_rethrow } from "next/navigation";
import { connection } from "next/server";
import type { ReactNode } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { api, type CatchUp, type Me, type TodaysChallenge } from "@/lib/api";

/**
 * Home: one card per Active Stack, with its Streak, today's Daily Challenge (Play, Continue, or
 * the score and a Replay) and links to its Week map and its Archive; a link to Review, which
 * spans every Active Stack; and, when there are past Challenges not played yet, a link to
 * Catch-up (#19), which spans every Active Stack too and is optional. A first sign-in has no Active Stack yet, so it goes to onboarding. Each Stack's
 * card is its own section.
 */
export default async function Home() {
  await connection();
  const me = await api<Me>("/me");
  if (!me || me.needs_onboarding) redirect("/onboarding");
  const todays = await Promise.all(me.active_stacks.map((stack) => loadToday(stack.id)));
  const catchUp = await api<CatchUp>("/catch-up");

  return (
    <main>
      <PageHeader
        title="Your Stacks"
        description="Today's Daily Challenge for each Stack you study: three Questions, the same for everyone, released at 00:00 UTC."
        actions={
          <Button asChild variant="outline" size="lg">
            <Link href="/settings">
              <Settings aria-hidden />
              Change Active Stacks
            </Link>
          </Button>
        }
      />
      <ul
        className={cn(
          "grid list-none gap-5 p-0",
          me.active_stacks.length > 1 && "md:grid-cols-2",
        )}
      >
        {me.active_stacks.map((stack, i) => (
          <li key={stack.id} className="flex">
            <section
              className="flex w-full flex-col overflow-hidden rounded-2xl border bg-card shadow-xs"
              aria-labelledby={`stack-${stack.id}`}
            >
              <div className="flex items-start justify-between gap-3 px-5 pt-5">
                <h2
                  id={`stack-${stack.id}`}
                  className="font-heading text-lg font-semibold tracking-tight"
                >
                  {stack.name}
                </h2>
                {todays[i] && <StreakLine streak={todays[i].streak} />}
              </div>
              <div className="flex-1 px-5 py-4">
                <TodaysChallengeLine stackId={stack.id} today={todays[i]} />
              </div>
              <div className="flex gap-1 border-t bg-muted/40 px-3 py-2">
                <Button asChild variant="ghost" size="sm">
                  <Link href={`/stacks/${encodeURIComponent(stack.id)}`}>
                    <MapIcon aria-hidden />
                    Week map
                  </Link>
                </Button>
                <Button asChild variant="ghost" size="sm">
                  <Link href={`/stacks/${encodeURIComponent(stack.id)}/archive`}>
                    <Archive aria-hidden />
                    Archive
                  </Link>
                </Button>
              </div>
            </section>
          </li>
        ))}
      </ul>

      <div className="mt-5 grid gap-5 md:grid-cols-2">
        <Tile
          icon={<Repeat aria-hidden className="size-5" />}
          link={<Link href="/review">Review</Link>}
        >
          Practise Missed Questions and past Lessons from all your Stacks, whenever you like.
        </Tile>
        <CatchUpLine catchUp={catchUp} />
      </div>
    </main>
  );
}

/** A card that is one big link, with the link's own text kept short for screen readers. */
function Tile({ icon, link, children }: { icon: ReactNode; link: ReactNode; children: ReactNode }) {
  return (
    <div className="group relative flex items-start gap-4 rounded-2xl border bg-card p-5 shadow-xs transition-colors hover:border-primary/50 hover:bg-accent/30">
      <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
        {icon}
      </span>
      <div className="min-w-0 flex-1 space-y-1">
        <p className="font-heading font-semibold [&_a]:after:absolute [&_a]:after:inset-0 [&_a]:after:rounded-2xl [&_a]:focus-visible:outline-none [&_a:focus-visible]:after:ring-3 [&_a:focus-visible]:after:ring-ring/50">
          {link}
        </p>
        <p className="text-sm text-muted-foreground">{children}</p>
      </div>
      <ArrowRight
        aria-hidden
        className="mt-1 size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary"
      />
    </div>
  );
}

/**
 * A Stack's Streak: consecutive Days whose Challenge the Learner finished on its Day. Today's,
 * until played, doesn't break it, and a Day with no Challenge is skipped.
 */
function StreakLine({ streak }: { streak: number }) {
  if (streak === 0) {
    return (
      <p className="shrink-0 rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
        No Streak running
      </p>
    );
  }
  return (
    <p className="shrink-0 rounded-full bg-streak/15 px-2.5 py-1 text-xs font-semibold text-streak">
      🔥 {streak}-Day Streak
    </p>
  );
}

/** Catch-up across every Active Stack: the past Challenges not played yet, if any. Optional. */
function CatchUpLine({ catchUp }: { catchUp: CatchUp | null }) {
  const count = catchUp?.stacks.reduce((sum, s) => sum + s.count, 0) ?? 0;
  if (count === 0) return null;
  return (
    <Tile
      icon={<History aria-hidden className="size-5" />}
      link={<Link href="/catch-up">Catch-up</Link>}
    >
      {count} past Challenge{count === 1 ? "" : "s"} you haven&apos;t played. Optional.
    </Tile>
  );
}

/**
 * A Stack's Daily Challenge for today, or null when it couldn't be loaded: a failed request must
 * not look like a Day with no Challenge. The API's redirects (sign-in, onboarding) still apply.
 */
async function loadToday(stackId: string): Promise<TodaysChallenge | null> {
  try {
    return await api<TodaysChallenge>(`/stacks/${encodeURIComponent(stackId)}/challenges/today`);
  } catch (error) {
    unstable_rethrow(error);
    console.error(error);
    return null;
  }
}

/**
 * A Stack's Daily Challenge for today (UTC): Play, Continue, or "Played: 2/3 · Replay"; "No
 * Challenge today" when none is written for the Day, and a notice when it couldn't be loaded.
 */
function TodaysChallengeLine({
  stackId,
  today,
}: {
  stackId: string;
  today: TodaysChallenge | null;
}) {
  if (!today) {
    return (
      <div
        role="alert"
        className="flex h-full items-center gap-3 rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-5 text-sm"
      >
        <CircleAlert aria-hidden className="size-5 shrink-0 text-destructive" />
        <p>Today&apos;s Challenge couldn&apos;t be loaded. Reload the page to try again.</p>
      </div>
    );
  }
  const challenge = today.challenge;
  if (!challenge) {
    return (
      <div className="flex h-full items-center gap-3 rounded-xl border border-dashed px-4 py-5 text-sm">
        <CalendarDays aria-hidden className="size-5 text-muted-foreground" />
        <p className="text-muted-foreground">No Challenge today</p>
      </div>
    );
  }
  const href = `/stacks/${encodeURIComponent(stackId)}/challenge`;
  const finished = challenge.status === "finished";
  return (
    <div className="flex h-full flex-col justify-between gap-4 rounded-xl bg-linear-to-br from-primary/10 via-primary/5 to-transparent px-4 py-4 ring-1 ring-primary/15">
      <div className="space-y-1">
        <p className="text-xs font-medium tracking-wide text-primary uppercase">Daily Challenge</p>
        <p className="font-heading text-base font-semibold">{challenge.label}</p>
      </div>
      {finished ? (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-sm font-semibold">
            Played: {challenge.score}/{challenge.out_of}
          </span>
          <Button asChild variant="outline">
            <Link href={href}>Replay</Link>
          </Button>
        </div>
      ) : (
        <Button asChild size="lg" className="self-start px-4">
          <Link href={href}>
            <Play aria-hidden />
            {challenge.status === "in_progress" ? "Continue" : "Play"}
          </Link>
        </Button>
      )}
    </div>
  );
}
