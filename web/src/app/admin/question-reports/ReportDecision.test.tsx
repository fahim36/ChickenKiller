import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { QuestionReport } from "@/lib/api";
import { ReportDecision } from "./ReportDecision";
import { decideReport } from "./actions";

vi.mock("./actions", () => ({ decideReport: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
const report: QuestionReport = {
  id: "report-1",
  stack_id: "mini",
  question_id: "q1",
  category: "wrong_answer",
  note: null,
  status: "open",
  explanation: null,
  created_at: "2026-10-11",
  updated_at: "2026-10-11",
};
it("requires an explanation and displays acceptance awaiting publication", async () => {
  vi.mocked(decideReport).mockResolvedValue({
    ...report,
    status: "accepted",
    explanation: "Confirmed defect.",
  });
  render(<ReportDecision initial={report} />);
  expect(
    screen
      .getByRole("button", { name: "Save decision" })
      .hasAttribute("disabled"),
  ).toBe(true);
  fireEvent.change(screen.getByLabelText("Admin explanation (required)"), {
    target: { value: "Confirmed defect." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save decision" }));
  expect(
    await screen.findByText("Status: Accepted, awaiting publication"),
  ).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Save decision" })).toBeNull();
  expect(screen.getByRole("button", { name: "Save correction association" })).toBeTruthy();
  expect(decideReport).toHaveBeenCalledWith(
    "report-1",
    "accepted",
    "Confirmed defect.",
  );
});

it("retains an explanation after a failed decision and permits retry", async () => {
  vi.mocked(decideReport).mockRejectedValue(new Error("Already decided"));
  render(<ReportDecision initial={report} />);
  fireEvent.change(screen.getByLabelText("Decision"), {
    target: { value: "closed" },
  });
  fireEvent.change(screen.getByLabelText("Admin explanation (required)"), {
    target: { value: "Duplicate." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save decision" }));
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(
    (
      screen.getByLabelText(
        "Admin explanation (required)",
      ) as HTMLTextAreaElement
    ).value,
  ).toBe("Duplicate.");
  expect(
    screen
      .getByRole("button", { name: "Save decision" })
      .hasAttribute("disabled"),
  ).toBe(false);
});
