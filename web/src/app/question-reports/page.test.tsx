import { formatLocalTime } from "@/components/LocalTime";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { stubApi } from "@/test/stubApi";
import YourReports from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
it("shows private report statuses, notes and Admin explanations, with Open-only editing", async () => {
  stubApi({
    "/me/question-reports": [
      {
        id: "1",
        category: "wrong_answer",
        stack_id: "mini",
        question_id: "q1",
        status: "open",
        note: "First note",
        explanation: null,
        updated_at: "2026-10-11",
      },
      {
        id: "2",
        category: "broken_source",
        stack_id: "mini",
        question_id: "q2",
        status: "closed",
        note: null,
        explanation: "Duplicate of a published correction.",
        updated_at: "2026-10-11",
      },
    ],
  });
  render(await YourReports());
  expect(screen.getByText("First note")).toBeTruthy();
  expect(screen.getByText("Status: Closed")).toBeTruthy();
  expect(screen.getByText(/Duplicate of a published correction/)).toBeTruthy();
  expect(
    screen.getAllByRole("link", { name: "Edit Open report" }),
  ).toHaveLength(1);
});

it("shows the imported correction and its retirement reason on a resolved report", async () => {
  stubApi({
    "/me/question-reports": [
      {
        id: "1",
        category: "outdated_claim",
        stack_id: "mini",
        question_id: "q1",
        status: "resolved",
        note: null,
        explanation: "Confirmed.",
        updated_at: "2026-10-11",
        correction_kind: "replacement",
        replacement_id: "q2",
        resolved_at: "2026-10-11T10:00:00Z",
        resolution_reason: "Obsolete premise.",
      },
    ],
  });
  render(await YourReports());
  expect(screen.getByText("Status: Resolved")).toBeTruthy();
  expect(screen.getByText(/^Correction imported/).textContent).toContain(
    formatLocalTime("2026-10-11T10:00:00Z"),
  );
  expect(screen.getByText(/Retirement reason: Obsolete premise/)).toBeTruthy();
  expect(screen.queryByRole("link", { name: "Edit Open report" })).toBeNull();
});
