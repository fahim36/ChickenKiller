import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Draft } from "@/lib/api";
import { ONBOARDED, stubApi } from "@/test/stubApi";
import DraftsPage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("next/cache", () => ({ revalidatePath: () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const DRAFTS: Draft[] = [
  {
    id: 7,
    stack_id: "agentic-ai-engineer",
    kind: "questions",
    status: "pending",
    author_email: "ada@example.com",
    note: "Two on tool use.",
    payload: { questions: [{ id: "w01-l01-q90", type: "multiple_choice", prompt: "Why?" }] },
    created_at: "2026-09-27T10:00:00Z",
    decided_at: null,
  },
  {
    id: 6,
    stack_id: "agentic-ai-engineer",
    kind: "challenge",
    status: "rejected",
    author_email: "bo@example.com",
    note: "",
    payload: { day: "2026-10-05", questions: ["a", "b", "c"] },
    created_at: "2026-09-26T10:00:00Z",
    decided_at: "2026-09-26T12:00:00Z",
  },
];

it("lists each draft with its author, and offers a decision only on pending ones", async () => {
  stubApi({ "/me": { ...ONBOARDED, is_admin: true }, "/admin/drafts": DRAFTS });

  render(await DraftsPage());

  const [pending, rejected] = Array.from(
    screen.getByRole("list", { name: "Drafts" }).children,
  ) as HTMLElement[];
  expect(pending.textContent).toContain("by ada@example.com");
  expect(within(pending).getByRole("button", { name: "Accept" })).toBeTruthy();
  expect(rejected.textContent).toContain("Daily Challenge for 2026-10-05");
  expect(within(rejected).queryByRole("button", { name: "Accept" })).toBeNull();
});

it("is hidden from anyone but the Admin", async () => {
  stubApi({ "/me": ONBOARDED });

  await expect(DraftsPage()).rejects.toThrow(
    expect.objectContaining({ digest: expect.stringContaining("404") }),
  );
});
