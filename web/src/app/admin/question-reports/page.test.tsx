import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ONBOARDED, stubApi } from "@/test/stubApi";
import ReportQueue from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("keeps non-Admins out of the report queue", async () => {
  const fetch = stubApi({ "/me": { ...ONBOARDED, is_admin: false } });
  await expect(ReportQueue()).rejects.toThrow();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("groups reports by Question and shows decisions with required explanations", async () => {
  const report = {
    id: "1",
    stack_id: "mini",
    question_id: "q1",
    category: "wrong_answer",
    note: "Check the premise.",
    status: "open",
    explanation: null,
    created_at: "2026-10-11",
    updated_at: "2026-10-11",
    reporter_email: "first@example.com",
  };
  stubApi({
    "/me": { ...ONBOARDED, is_admin: true },
    "/admin/question-reports": [
      {
        stack_id: "mini",
        question_id: "q1",
        prompt: "Which claim is valid?",
        retired_reason: null,
        reports: [
          report,
          {
            ...report,
            id: "2",
            status: "accepted",
            explanation: "Confirmed defect.",
            reporter_email: "second@example.com",
          },
        ],
      },
    ],
  });
  render(await ReportQueue());
  const group = screen.getByRole("list", { name: "Reports for q1" });
  expect(within(group).getByText(/first@example.com/)).toBeTruthy();
  expect(within(group).getByText(/second@example.com/)).toBeTruthy();
  expect(screen.getByText("2 reports")).toBeTruthy();
  expect(
    screen.getByText("Status: Accepted, awaiting publication"),
  ).toBeTruthy();
  expect(screen.getAllByRole("button", { name: "Save decision" })).toHaveLength(
    1,
  );
});
