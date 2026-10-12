"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { startPlacement } from "./actions";
import type { PlacementEligibility } from "./types";

export function PlacementEntry({
  stack,
  week,
  eligibility,
  enabled,
}: {
  stack: string;
  week: string;
  eligibility: PlacementEligibility;
  enabled: boolean;
}) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  async function start() {
    setPending(true);
    try {
      const attempt = await startPlacement(stack, week);
      router.push(`/placements/${encodeURIComponent(attempt.id)}`);
    } catch {
      setError(
        "Placement could not start. Refresh to check current coverage and eligibility.",
      );
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="rounded border p-4 space-y-3">
      <h2 className="text-xl font-semibold">Placement Quiz</h2>
      <p>
        Test the whole Week to complete its Lessons. Requires 80% overall and in
        every Lesson. Milestones stay separate.
      </p>
      {eligibility.attempt_id ? (
        <Link
          href={`/placements/${encodeURIComponent(eligibility.attempt_id)}`}
        >
          Resume Placement Quiz
        </Link>
      ) : !enabled ? (
        <p>Placement is being verified before release.</p>
      ) : eligibility.available ? (
        <button type="button" disabled={pending} onClick={start}>
          {pending ? "Starting…" : "Start Placement Quiz"}
        </button>
      ) : (
        <p>{eligibility.reason}</p>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
