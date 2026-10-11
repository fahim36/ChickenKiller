import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { QuestionReport } from "@/lib/api";
import { CorrectionForm } from "./CorrectionForm";
import { associateCorrection } from "./actions";

vi.mock("./actions", () => ({ associateCorrection: vi.fn() }));
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
  status: "accepted",
  explanation: "Confirmed.",
  created_at: "2026-10-11",
  updated_at: "2026-10-11",
};
it("requires a replacement ID and saves the expected correction without claiming resolution", async () => {
  vi.mocked(associateCorrection).mockResolvedValue({
    ...report,
    correction_kind: "replacement",
    replacement_id: "q2",
  });
  render(<CorrectionForm initial={report} />);
  fireEvent.change(screen.getByLabelText("Correction outcome"), {
    target: { value: "replacement" },
  });
  expect(
    screen
      .getByRole("button", { name: "Save correction association" })
      .hasAttribute("disabled"),
  ).toBe(true);
  fireEvent.change(
    screen.getByLabelText("Replacement Question ID (required)"),
    { target: { value: "q2" } },
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Save correction association" }),
  );
  expect(await screen.findByRole("status")).toBeTruthy();
  expect(associateCorrection).toHaveBeenCalledWith(
    "report-1",
    "replacement",
    "q2",
  );
  expect(screen.getByText(/replace it with q2/)).toBeTruthy();
  expect(screen.queryByText(/Correction imported/)).toBeNull();
});

it("retains the plan after an association failure", async () => {
  vi.mocked(associateCorrection).mockRejectedValue(
    new Error("Already resolved"),
  );
  render(<CorrectionForm initial={report} />);
  fireEvent.click(
    screen.getByRole("button", { name: "Save correction association" }),
  );
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.queryByRole("status")).toBeNull();
});
