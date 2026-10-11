import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Page from "./page";
import { api } from "@/lib/api";

vi.mock("next/server", () => ({ connection: vi.fn() }));
vi.mock("next/navigation", () => ({
  notFound: vi.fn(() => {
    throw Error("not found");
  }),
}));
vi.mock("@/lib/api", () => ({ api: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

it("shows actionable coverage gaps and absence", async () => {
  vi.mocked(api)
    .mockResolvedValueOnce({ is_admin: true })
    .mockResolvedValueOnce([
      {
        id: "stack",
        name: "Stack",
        weeks: [
          {
            id: "w01",
            title: "First Week",
            status: "gaps",
            gaps: ["Lesson: fewer than 5 suitable Questions"],
            plan: null,
          },
          {
            id: "w02",
            title: "Second Week",
            status: "absent",
            gaps: [],
            plan: null,
          },
        ],
      },
    ]);
  render(await Page());
  expect(
    screen.getByText("Lesson: fewer than 5 suitable Questions"),
  ).toBeTruthy();
  expect(screen.getByText("No reviewed placement plan")).toBeTruthy();
});

it("refuses non-Admin access before reading plans", async () => {
  vi.mocked(api).mockResolvedValueOnce({ is_admin: false });
  await expect(Page()).rejects.toThrow("not found");
  expect(api).toHaveBeenCalledTimes(1);
});
