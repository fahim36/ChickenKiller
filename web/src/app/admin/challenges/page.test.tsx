import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { ChallengesAhead, Me } from "@/lib/api";
import { ONBOARDED, stubApi } from "@/test/stubApi";
import ChallengesPage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

const ADMIN: Me = { ...ONBOARDED, email: "admin@example.com", is_admin: true };

const AHEAD: ChallengesAhead[] = [
  {
    stack_id: "agentic-ai-engineer",
    stack_name: "Agentic AI Engineer",
    written_through: "2026-10-03",
    days_left: 7,
    warning: false,
  },
  {
    stack_id: "data-engineer",
    stack_name: "Data Engineer",
    written_through: "2026-10-01",
    days_left: 1,
    warning: true,
  },
  {
    stack_id: "new-stack",
    stack_name: "New Stack",
    written_through: null,
    days_left: 0,
    warning: true,
  },
];

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows how far ahead each Stack's Challenges are written, and warns below three Days", async () => {
  stubApi({ "/me": ADMIN, "/admin/challenges": AHEAD });

  render(await ChallengesPage());

  const list = screen.getByRole("list", { name: "Upcoming Challenges" });
  const rows = within(list).getAllByRole("listitem");
  expect(rows.map((li) => li.textContent)).toEqual([
    "Agentic AI Engineer: Challenges written through 3 Oct 2026 (7 Days left)",
    expect.stringContaining("Data Engineer: Challenges written through 1 Oct 2026 (1 Day left)"),
    expect.stringContaining("New Stack: No Challenges written (0 Days left)"),
  ]);
  expect(within(rows[0]).queryByText(/Write more/)).toBeNull();
  expect(within(rows[1]).getByText(/Write more with/).textContent).toContain(
    "/write-challenges data-engineer",
  );
});

it("is not found for a Learner who isn't the Admin", async () => {
  stubApi({ "/me": ONBOARDED, "/admin/challenges": AHEAD });

  await expect(ChallengesPage()).rejects.toThrow(
    expect.objectContaining({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" }),
  );
});
