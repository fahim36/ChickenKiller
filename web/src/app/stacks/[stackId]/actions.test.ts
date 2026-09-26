import { afterEach, expect, it, vi } from "vitest";
import { setMilestoneTicked } from "./actions";

vi.mock("next/cache", () => ({ refresh: () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => vi.unstubAllGlobals());

it("saves a Milestone tick for the Learner on that Stack", async () => {
  const fetch = vi.fn(async () => Response.json({ id: "w01-m01", ticked: true }));
  vi.stubGlobal("fetch", fetch);

  const saved = await setMilestoneTicked("agentic-ai-engineer", "w01-m01", true);

  expect(saved).toEqual({ id: "w01-m01", ticked: true });
  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/stacks/agentic-ai-engineer/milestones/w01-m01",
    expect.objectContaining({ method: "PUT", body: JSON.stringify({ ticked: true }) }),
  );
});

it("fails when the API refuses the tick", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 404 })));

  await expect(setMilestoneTicked("agentic-ai-engineer", "nope", true)).rejects.toThrow();
});
