"use server";

import { refresh } from "next/cache";
import { apiPut, type MilestoneTick } from "@/lib/api";

/** Tick or untick one of the Active Stack's Milestones. Ticks never change any lock state. */
export async function setMilestoneTicked(
  stackId: string,
  milestoneId: string,
  ticked: boolean,
): Promise<MilestoneTick> {
  const saved = await apiPut<MilestoneTick>(
    `/stacks/${encodeURIComponent(stackId)}/milestones/${encodeURIComponent(milestoneId)}`,
    { ticked },
  );
  refresh();
  return saved;
}
