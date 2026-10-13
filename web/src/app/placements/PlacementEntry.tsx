"use client";

import Link from "next/link";
import {
  ArrowRight,
  Clock3,
  GraduationCap,
  Layers3,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
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
    <section className="relative overflow-hidden rounded-3xl border border-primary/20 bg-linear-to-br from-primary/10 via-card to-background p-6 shadow-xs sm:p-8">
      <div className="mb-5 flex items-center gap-3">
        <span className="flex size-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-sm">
          <GraduationCap aria-hidden className="size-6" />
        </span>
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Know it already?
          </p>
          <h2 className="font-heading text-2xl font-semibold">
            Placement Quiz
          </h2>
        </div>
      </div>
      <p className="max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base">
        Test the whole Week to complete its Lessons. Requires 80% overall and in
        every Lesson. Milestones stay separate.
      </p>
      <div className="my-6 grid grid-cols-3 gap-2 text-sm">
        {[
          { icon: ShieldCheck, title: "80%", detail: "Every Lesson" },
          { icon: Layers3, title: "Whole Week", detail: "Full coverage" },
          { icon: Clock3, title: "Your pace", detail: "Save & resume" },
        ].map(({ icon: Icon, title, detail }) => (
          <div
            key={title}
            className="rounded-2xl border border-border/60 bg-background/70 p-3"
          >
            <Icon aria-hidden className="mb-2 size-4 text-primary" />
            <p className="font-semibold">{title}</p>
            <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {eligibility.attempt_id ? (
          <Button asChild size="lg">
            <Link
              href={`/placements/${encodeURIComponent(eligibility.attempt_id)}`}
            >
              Resume Placement Quiz <ArrowRight aria-hidden />
            </Link>
          </Button>
        ) : !enabled ? (
          <p className="text-sm text-muted-foreground">
            Placement is being verified before release.
          </p>
        ) : eligibility.available ? (
          <Button size="lg" type="button" disabled={pending} onClick={start}>
            {pending ? "Starting…" : "Start Placement Quiz"}
            <ArrowRight aria-hidden />
          </Button>
        ) : (
          <p className="rounded-xl bg-background/70 p-3 text-sm text-muted-foreground">
            {eligibility.reason}
          </p>
        )}
        {error && <p role="alert">{error}</p>}
        {eligibility.result_id && (
          <Button asChild variant="outline">
            <Link
              href={`/placements/${encodeURIComponent(eligibility.result_id)}`}
            >
              View placement result
            </Link>
          </Button>
        )}
      </div>
    </section>
  );
}
