import { afterEach, expect, it, vi } from "vitest";
import { NEW_LEARNER, ONBOARDED, stubApi } from "@/test/stubApi";
import Home from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => vi.unstubAllGlobals());

it("sends a first sign-in to onboarding", async () => {
  stubApi({ "/me": NEW_LEARNER });

  await expect(Home()).rejects.toThrow(
    expect.objectContaining({ digest: expect.stringContaining(";/onboarding;") }),
  );
});

it("lands a returning Learner on their Active Stack", async () => {
  stubApi({ "/me": ONBOARDED });

  await expect(Home()).rejects.toThrow(
    expect.objectContaining({ digest: expect.stringContaining(";/stacks/agentic-ai-engineer;") }),
  );
});
