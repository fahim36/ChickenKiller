import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { stubApi } from "@/test/stubApi";
import ContentHealthPage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("next/navigation", () => ({
  notFound: () => {
    throw new Error("not-found");
  },
}));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "token" }),
}));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("blocks non-admins before fetching health evidence", async () => {
  const fetch = stubApi({ "/me": { is_admin: false } });
  await expect(ContentHealthPage()).rejects.toThrow("not-found");
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("distinguishes unavailable data from an empty imported inventory", async () => {
  stubApi({ "/me": { is_admin: true }, "/admin/content-health": null });
  render(await ContentHealthPage());
  expect(screen.getByText(/Content health is unavailable/)).toBeTruthy();
  cleanup();
  stubApi({ "/me": { is_admin: true }, "/admin/content-health": [] });
  render(await ContentHealthPage());
  expect(screen.getByText(/No Stacks are imported/)).toBeTruthy();
});

it("shows maintenance counts, quiz mix and original provenance without claiming healthy links", async () => {
  stubApi({
    "/me": { is_admin: true },
    "/admin/content-health": [
      {
        id: "s",
        name: "Test Stack",
        syllabus_version: "v2026-10-10",
        active_questions: 8,
        retired_questions: 2,
        thin_concepts: 1,
        retired_only_concepts: 1,
        untested_concepts: 1,
        without_current_lesson: 1,
        unresolved_reports: 3,
        source_urls: 25,
        concepts: [
          {
            id: "c",
            name: "Concept",
            active_questions: 2,
            multiple_choice: 1,
            multiple_select: 1,
            legacy_written: 0,
            status: "thin",
          },
        ],
        lessons: [
          {
            id: "l",
            title: "Lesson",
            active_questions: 8,
            multiple_choice: 6,
            multiple_select: 0,
            legacy_written: 2,
            quiz_eligible: true,
          },
        ],
        sources: [
          {
            url: "https://example.com",
            title: "Primary Source",
            oldest_accessed: "2026-09-26",
            latest_accessed: "2026-10-10",
            questions: 2,
          },
        ],
      },
    ],
  });
  render(await ContentHealthPage());
  expect(screen.getByText(/3 unresolved reports/)).toBeTruthy();
  expect(
    screen.getByText(/6 MC, 0 MS, 2 legacy written; quiz eligible/),
  ).toBeTruthy();
  expect(screen.getByText(/1 oldest URL groups of 25/)).toBeTruthy();
  expect(
    screen.getByText(/Original research dates, not revalidation dates/),
  ).toBeTruthy();
  expect(
    screen
      .getByRole("link", { name: /Saved link-check reports/ })
      .getAttribute("href"),
  ).toContain("actions/workflows/content-links.yml");
  expect(screen.queryByText(/All links healthy/)).toBeNull();
});
