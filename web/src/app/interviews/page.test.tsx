import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import InterviewsPage from "./page";
import { api } from "@/lib/api";
import { deleteInterview, loadInterviewSession } from "./actions";
import type { InterviewSession } from "./types";

vi.mock("next/server", () => ({ connection: vi.fn() }));
vi.mock("@/lib/api", () => ({ api: vi.fn() }));
vi.mock("./actions", () => ({
  deleteInterview: vi.fn(),
  loadInterviewSession: vi.fn(),
}));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

it("opens and deletes inactive Stack history with zero Active Stacks", async () => {
  const row: InterviewSession = {
    id: "private",
    stack_id: "python",
    expires_at: "2026-11-11T00:00:00Z",
    prompts: [
      {
        id: "scenario",
        concept: "aliases",
        lesson: "w01-l01",
        scenario: "Explain aliases",
        rubric: ["Distinguish references"],
        misconceptions: [],
      },
    ],
    responses: { scenario: "Saved text" },
    practice_state: "inactive_stack",
    ai_enabled: false,
  };
  vi.mocked(api).mockImplementation(async (path) =>
    path === "/me" ? { active_stacks: [] } : [row],
  );
  vi.mocked(loadInterviewSession).mockResolvedValue(row);
  vi.mocked(deleteInterview).mockResolvedValue(undefined);
  render(await InterviewsPage({ searchParams: Promise.resolve({}) }));
  expect(api).toHaveBeenCalledWith("/me/interviews");
  fireEvent.click(screen.getByRole("button", { name: /Open session.*python/ }));
  expect(await screen.findByText("Saved text")).toBeTruthy();
  expect(screen.getByRole("status").textContent).toContain("inactive stack");
  const remove = screen.getByRole("button", { name: "Delete session" });
  await waitFor(() => expect(remove.hasAttribute("disabled")).toBe(false));
  fireEvent.click(remove);
  await waitFor(() => expect(screen.queryByText("Saved text")).toBeNull());
  expect(deleteInterview).toHaveBeenCalledWith("private");
});
