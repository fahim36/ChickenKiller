import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { TargetedReviewVisit } from "./TargetedReviewVisit";
import { recordTargetedReviewVisit } from "./actions";

vi.mock("./actions", () => ({ recordTargetedReviewVisit: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

it("records the loaded target without sending an answer or blocking rendering on failure", async () => {
  vi.mocked(recordTargetedReviewVisit).mockRejectedValue(new Error("offline"));
  const { container } = render(
    <>
      <TargetedReviewVisit stack="mini-stack" concept="concept-a" />
      <p>Review remains available</p>
    </>,
  );
  await waitFor(() =>
    expect(recordTargetedReviewVisit).toHaveBeenCalledWith(
      "mini-stack",
      "concept-a",
    ),
  );
  expect(container.textContent).toBe("Review remains available");
});
