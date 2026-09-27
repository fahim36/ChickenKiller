import Link from "next/link";
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
    return (
      <p>
        <Link href={href}>{name}</Link>{" "}
        <span>
          Played: {c.score}/{c.out_of}
        </span>
      </p>
    );
  }
  const action = c.status === "in_progress" ? "Continue" : "Play";
  return (
    <p>
      <strong>{name}</strong>{" "}
      <Link className="button" href={href} aria-label={`${action} ${name}`}>
        {action}
      </Link>
    </p>
  );
}

/** "Agentic AI Engineer #40 · 26 Sep" without the Stack's name: "#40 · 26 Sep". */
export function shortLabel(label: string): string {
  const at = label.lastIndexOf("#");
  return at < 0 ? label : label.slice(at);
}
