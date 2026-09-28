import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { DeleteStackRequest } from "./DeleteStackRequest";

afterEach(cleanup);

it("asks once more before deleting, and can keep the Stack", () => {
  const action = vi.fn(async () => {});
  render(<DeleteStackRequest stackId="data-engineer" name="Data Engineer" action={action} />);

  fireEvent.click(screen.getByRole("button", { name: "Delete Data Engineer" }));
  expect(screen.getByText("Delete Data Engineer and all its drafts?")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Keep it" }));
  expect(action).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "Delete Data Engineer" }));
  fireEvent.click(screen.getByRole("button", { name: "Delete for good" }));
  expect(action).toHaveBeenCalledWith("data-engineer");
});
