"use client";

import { Briefcase, Check, Hammer } from "lucide-react";
import { useState } from "react";
import { Inline } from "@/components/Inline";
import { Notice } from "@/components/Notice";
import type { Milestone, MilestoneTick } from "@/lib/api";

/**
 * A Week's Milestones as a checklist the Learner ticks off themselves. Each tick is saved at
 * once through `tickAction`; if saving fails, the box goes back and the Learner is told.
 */
export function MilestoneChecklist({
  milestones,
  tickAction,
}: {
  milestones: Milestone[];
  tickAction: (milestoneId: string, ticked: boolean) => Promise<MilestoneTick>;
}) {
  const [ticked, setTicked] = useState(
    () => new Map(milestones.map((m) => [m.id, m.ticked] as const)),
  );
  const [failed, setFailed] = useState<Milestone | null>(null);

  function show(id: string, value: boolean) {
    setTicked((current) => new Map(current).set(id, value));
  }

  async function toggle(milestone: Milestone, value: boolean) {
    setFailed(null);
    show(milestone.id, value);
    try {
      const saved = await tickAction(milestone.id, value);
      show(saved.id, saved.ticked);
    } catch {
      show(milestone.id, !value);
      setFailed(milestone);
    }
  }

  return (
    <>
      <ul className="grid gap-2" aria-label="Milestones">
        {milestones.map((m) => {
          const KindIcon = m.kind === "build" ? Hammer : Briefcase;
          return (
            <li key={m.id}>
              <label className="relative flex cursor-pointer items-start gap-3 rounded-xl border bg-background px-3 py-2.5 text-sm transition-colors hover:bg-muted/60 has-checked:border-success/30 has-checked:bg-success/5 has-focus-visible:ring-3 has-focus-visible:ring-ring/40">
                <input
                  type="checkbox"
                  checked={ticked.get(m.id) ?? false}
                  onChange={(event) => toggle(m, event.target.checked)}
                  className="peer sr-only"
                />
                <span
                  aria-hidden
                  className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-md border bg-card text-transparent transition-colors peer-checked:border-success peer-checked:bg-success peer-checked:text-white"
                >
                  <Check className="size-3.5" strokeWidth={3} />
                </span>
                <span className="min-w-0 flex-1 peer-checked:text-muted-foreground peer-checked:line-through">
                  <span className="mr-2 inline-flex items-center gap-1 rounded-md bg-muted px-1.5 py-0.5 align-middle text-xs font-medium text-muted-foreground no-underline">
                    <KindIcon aria-hidden className="size-3" />
                    {m.kind === "build" ? "Build" : "Job hunt"}
                  </span>{" "}
                  <Inline text={m.title} />
                </span>
              </label>
            </li>
          );
        })}
      </ul>
      {failed && (
        <Notice tone="error" role="alert" className="mt-3">
          Couldn&apos;t save “{failed.title}”. Try again.
        </Notice>
      )}
    </>
  );
}
