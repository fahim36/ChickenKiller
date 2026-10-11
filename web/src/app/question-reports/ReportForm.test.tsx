import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { QuestionReport } from "@/lib/api";
import { ReportForm } from "./ReportForm";
import { saveReport } from "./actions";

vi.mock("./actions", () => ({ saveReport: vi.fn() }));
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
  created_at: "2026-10-11T00:00:00Z",
  updated_at: "2026-10-11T00:00:00Z",
};

it("requires a category and saves private feedback with an optional note", async () => {
  vi.mocked(saveReport).mockResolvedValue(report);
  render(<ReportForm stackId="mini" questionId="q1" initial={null} />);
  const button = screen.getByRole("button", { name: "Submit report" });
  expect(button.hasAttribute("disabled")).toBe(true);
  for (const label of [
    "Wrong answer",
    "Ambiguous wording",
    "Outdated claim",
    "Broken Source",
  ])
    expect(screen.getByRole("option", { name: label })).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Category (required)"), {
    target: { value: "wrong_answer" },
  });
  fireEvent.change(screen.getByLabelText("Supporting note (optional)"), {
    target: { value: "The premise differs." },
  });
  fireEvent.click(button);
  expect(await screen.findByRole("status")).toBeTruthy();
  expect(saveReport).toHaveBeenCalledWith(
    "mini",
    "q1",
    "wrong_answer",
    "The premise differs.",
  );
  expect(screen.getByText(/Status: Open/)).toBeTruthy();
});

it("loads an Open report for editing and preserves fields on failure", async () => {
  vi.mocked(saveReport).mockRejectedValue(new Error("Unavailable"));
  render(
    <ReportForm
      stackId="mini"
      questionId="q1"
      initial={{ ...report, note: "Old note" }}
    />,
  );
  expect(
    (screen.getByLabelText("Supporting note (optional)") as HTMLTextAreaElement)
      .value,
  ).toBe("Old note");
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(
    (screen.getByLabelText("Supporting note (optional)") as HTMLTextAreaElement)
      .value,
  ).toBe("Old note");
});

it("prevents edits while saving so success refers to the submitted values", async () => {
  let finish: (value: QuestionReport) => void = () => {};
  vi.mocked(saveReport).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  render(
    <ReportForm
      stackId="mini"
      questionId="q1"
      initial={{ ...report, note: "Note A" }}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  expect(
    screen.getByLabelText("Category (required)").hasAttribute("disabled"),
  ).toBe(true);
  expect(
    screen
      .getByLabelText("Supporting note (optional)")
      .hasAttribute("disabled"),
  ).toBe(true);
  expect(screen.queryByRole("status")).toBeNull();
  await act(async () => {
    finish({ ...report, note: "Note A" });
  });
  expect(screen.getByRole("status")).toBeTruthy();
  expect(
    (screen.getByLabelText("Supporting note (optional)") as HTMLTextAreaElement)
      .value,
  ).toBe("Note A");
  expect(
    screen
      .getByLabelText("Supporting note (optional)")
      .hasAttribute("disabled"),
  ).toBe(false);
});
