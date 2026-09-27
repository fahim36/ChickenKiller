import { CircleCheck, Play } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import type { ArchivedChallenge } from "@/lib/api";

/**
 * One Challenge in a Stack's Archive or in Catch-up: "#40 · 26 Sep", then the Learner's first
 * score ("Played: 2/3", linking to the Challenge for a replay), or Play / Continue.
 */
export function ArchiveLine({
  stackId,
  challenge: c,
}: {
  stackId: string;
  challenge: ArchivedChallenge;
}) {
  const href = `/stacks/${encodeURIComponent(stackId)}/archive/${c.number}`;
  const name = shortLabel(c.label);
  if (c.status === "finished") {
    const perfect = c.score === c.out_of;
    return (
      <p className="flex items-center justify-between gap-3 rounded-xl border bg-card px-4 py-3">
        <Link href={href} className="font-medium underline-offset-4 hover:text-primary hover:underline">
          {name}
        </Link>{" "}
        <span
          className={
            perfect
              ? "inline-flex items-center gap-1 rounded-full bg-success/12 px-2.5 py-0.5 text-sm font-medium text-success-foreground"
              : "inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-0.5 text-sm font-medium text-muted-foreground"
          }
        >
          {perfect && <CircleCheck aria-hidden className="size-3.5" />}
          <span>
            Played: {c.score}/{c.out_of}
          </span>
        </span>
      </p>
    );
  }
  const action = c.status === "in_progress" ? "Continue" : "Play";
  return (
    <p className="flex items-center justify-between gap-3 rounded-xl border bg-card px-4 py-3">
      <strong className="font-medium">{name}</strong>{" "}
      <Button asChild size="sm" variant={action === "Continue" ? "default" : "secondary"}>
        <Link href={href} aria-label={`${action} ${name}`}>
          <Play aria-hidden />
          {action}
        </Link>
      </Button>
    </p>
  );
}

/** "Agentic AI Engineer #40 · 26 Sep" without the Stack's name: "#40 · 26 Sep". */
export function shortLabel(label: string): string {
  const at = label.lastIndexOf("#");
  return at < 0 ? label : label.slice(at);
}
