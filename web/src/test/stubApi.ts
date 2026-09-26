import { vi } from "vitest";
import type { Me, StackSummary } from "@/lib/api";

export const NEW_LEARNER: Me = {
  email: "ada@example.com",
  is_admin: false,
  needs_onboarding: true,
  active_stacks: [],
};

/** A Learner studying one Stack. */
export const ONBOARDED: Me = {
  ...NEW_LEARNER,
  needs_onboarding: false,
  active_stacks: [
    { id: "agentic-ai-engineer", name: "Agentic AI Engineer", started_at: "2026-09-26T10:00:00Z" },
  ],
};

/** A Learner studying both of `STACKS`. */
export const ONBOARDED_TWICE: Me = {
  ...ONBOARDED,
  active_stacks: [
    ...ONBOARDED.active_stacks,
    { id: "data-engineer", name: "Data Engineer", started_at: "2026-09-27T10:00:00Z" },
  ],
};

export const STACKS: StackSummary[] = [
  { id: "agentic-ai-engineer", name: "Agentic AI Engineer", summary: "Agents.", version: "v1" },
  { id: "data-engineer", name: "Data Engineer", summary: "Pipelines.", version: "v1" },
];

/** Stand in for the API: `responses` maps a path to its JSON body; anything else is a 404. */
export function stubApi(responses: Record<string, unknown>) {
  const fetch = vi.fn(async (url: string) => {
    const path = new URL(url).pathname;
    return path in responses
      ? Response.json(responses[path])
      : new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}
