"use client";

import { useState } from "react";
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
      <ul className="milestones" aria-label="Milestones">
        {milestones.map((m) => (
          <li key={m.id}>
            <label>
              <input
                type="checkbox"
                checked={ticked.get(m.id) ?? false}
                onChange={(event) => toggle(m, event.target.checked)}
              />
              <span className={`tag tag-${m.kind}`}>
                {m.kind === "build" ? "Build" : "Job hunt"}
              </span>{" "}
              {m.title}
            </label>
          </li>
        ))}
      </ul>
      {failed && (
        <p role="alert" className="notice notice-error">
          Couldn&apos;t save “{failed.title}”. Try again.
        </p>
      )}
    </>
  );
}
