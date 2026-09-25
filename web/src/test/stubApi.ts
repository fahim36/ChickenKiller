import { vi } from "vitest";
import type { Me, StackSummary } from "@/lib/api";

export const NEW_LEARNER: Me = {
  email: "ada@example.com",
  is_admin: false,
  needs_onboarding: true,
  active_stack: null,
  time_zone: null,
};

export const ONBOARDED: Me = {
  ...NEW_LEARNER,
  needs_onboarding: false,
  active_stack: {
    id: "agentic-ai-engineer",
    name: "Agentic AI Engineer",
    started_at: "2026-09-26T10:00:00Z",
  },
  time_zone: "Asia/Dhaka",
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
