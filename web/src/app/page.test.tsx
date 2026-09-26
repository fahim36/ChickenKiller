import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { NEW_LEARNER, ONBOARDED_TWICE, stubApi } from "@/test/stubApi";
import Home from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("sends a first sign-in to onboarding", async () => {
  stubApi({ "/me": NEW_LEARNER });

  await expect(Home()).rejects.toThrow(
    expect.objectContaining({ digest: expect.stringContaining(";/onboarding;") }),
  );
});

it("gives each Active Stack its own card, linking to its Week map", async () => {
  stubApi({ "/me": ONBOARDED_TWICE });

  render(await Home());

  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Your Stacks");
  const cards = [
    ["Agentic AI Engineer", "/stacks/agentic-ai-engineer"],
    ["Data Engineer", "/stacks/data-engineer"],
  ];
  for (const [name, href] of cards) {
    const card = screen.getByRole("region", { name });
    expect(within(card).getByRole("link", { name: "Week map" }).getAttribute("href")).toBe(href);
  }
  expect(screen.getByRole("link", { name: "Add or drop Stacks" }).getAttribute("href")).toBe(
    "/settings",
  );
});
