"use server";

import { apiPost } from "@/lib/api";
import type { PlacementAttempt } from "./types";

export async function startPlacement(stack: string, week: string) {
  return apiPost<PlacementAttempt>(
    `/stacks/${encodeURIComponent(stack)}/weeks/${encodeURIComponent(week)}/placement`,
    {},
  );
}
export async function savePlacement(
  id: string,
  question: string,
  answer: string | string[] | null,
) {
  return apiPost<PlacementAttempt>(
    `/me/placements/${encodeURIComponent(id)}/save`,
    { question_id: question, answer },
  );
}
export async function abandonPlacement(id: string) {
  return apiPost<PlacementAttempt>(
    `/me/placements/${encodeURIComponent(id)}/abandon`,
    {},
  );
}

export async function submitPlacement(id: string) {
  return apiPost<PlacementAttempt>(
    `/me/placements/${encodeURIComponent(id)}/submit`,
    {},
  );
}
