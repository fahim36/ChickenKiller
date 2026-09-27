import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Archive, ArchivedChallenge } from "@/lib/api";
import { stubApi } from "@/test/stubApi";
import ArchivePage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function archived(number: number, day: number, extra: Partial<ArchivedChallenge> = {}) {
  return {
    number,
    day: `2026-09-${day}`,
    label: `Agentic AI Engineer #${number} · ${day} Sep`,
    status: "not_started",
    score: null,
    out_of: null,
    ...extra,
  } satisfies ArchivedChallenge;
}

const ARCHIVE: Archive = {
  stack_id: "agentic-ai-engineer",
  stack_name: "Agentic AI Engineer",
  day: "2026-09-27",
  challenges: [
    archived(3, 27),
    archived(2, 26, { status: "in_progress" }),
    archived(1, 25, { status: "finished", score: 2, out_of: 3 }),
  ],
};

async function renderPage(body: Archive | null) {
  stubApi(body ? { "/stacks/agentic-ai-engineer/challenges": body } : {});
  render(
    await ArchivePage({
      params: Promise.resolve({ stackId: "agentic-ai-engineer" }),
    } as never),
  );
}

it("lists every released Challenge newest first, by number and UTC date", async () => {
  await renderPage(ARCHIVE);

  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(
    "Agentic AI Engineer: Archive",
  );
  const items = screen.getAllByRole("listitem").map((li) => li.textContent);
  expect(items).toEqual(["#3 · 27 Sep Play", "#2 · 26 Sep Continue", "#1 · 25 Sep Played: 2/3"]);
});

it("links each Challenge to its page, to play it or see the first result and replay", async () => {
  await renderPage(ARCHIVE);

  const [newest, , played] = screen.getAllByRole("listitem");
  expect(within(newest).getByRole("link", { name: "Play #3 · 27 Sep" }).getAttribute("href")).toBe(
    "/stacks/agentic-ai-engineer/archive/3",
  );
  expect(within(played).getByRole("link", { name: "#1 · 25 Sep" }).getAttribute("href")).toBe(
    "/stacks/agentic-ai-engineer/archive/1",
  );
});

it("says that only today's Challenge counts toward a Streak", async () => {
  await renderPage(ARCHIVE);

  expect(
    screen.getByText(/only today's\s+Challenge, played today, counts toward your Streak/),
  ).toBeTruthy();
});

it("says so when nothing is released yet", async () => {
  await renderPage({ ...ARCHIVE, challenges: [] });

  expect(screen.getByRole("status").textContent).toBe("No Challenges released yet.");
});

it("is a 404 for a Stack the API doesn't know", async () => {
  await expect(renderPage(null)).rejects.toThrow(
    expect.objectContaining({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" }),
  );
});
