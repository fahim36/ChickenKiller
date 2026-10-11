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

it("shows coverage and unresolved teaching references without private responses", async () => {
  vi.mocked(api)
    .mockResolvedValueOnce({ is_admin: true })
    .mockResolvedValueOnce([
      {
        id: "python",
        name: "Python",
        reviewed_prompts: 1,
        covered_concepts: 1,
        concepts_without_prompts: ["lists"],
        prompts: [
          {
            id: "aliases-interview",
            concept: "aliases",
            lesson: "removed",
            version: 1,
            unresolved: true,
          },
        ],
      },
    ]);
  render(await Page());
  expect(screen.getByText("Unresolved teaching reference")).toBeTruthy();
  expect(
    screen.getByText("Concepts without interview prompts (1)"),
  ).toBeTruthy();
});

it("refuses non-Admin access before reading coverage", async () => {
  vi.mocked(api).mockResolvedValueOnce({ is_admin: false });
  await expect(Page()).rejects.toThrow("not found");
  expect(api).toHaveBeenCalledTimes(1);
});
