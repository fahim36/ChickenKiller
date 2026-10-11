import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { stubApi } from "@/test/stubApi";
import PracticeOutcomesPage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("next/navigation", () => ({
  notFound: () => {
    throw new Error("not-found");
  },
}));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "token" }),
}));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const data = {
  qualifying_answers: 1,
  correct_answers: 1,
  accuracy: 1,
  learners: 1,
  concepts: 1,
  uptake_days: 3,
  uptake_learners: 1,
  completed_practice_answers: 2,
  practice_learners: 1,
  retakes_total: 4,
  retakes_completed: 2,
  retakes_waived: 1,
};

it("shows small samples with denominators and descriptive limitations", async () => {
  stubApi({ "/me": { is_admin: true }, "/admin/practice-outcomes": data });
  render(await PracticeOutcomesPage());
  expect(
    screen.getByText(/100% correct: 1 of 1 qualifying answers/),
  ).toBeTruthy();
  expect(screen.getByText(/Content waivers: 1/)).toBeTruthy();
  expect(
    screen.getByText(/first recorded answer does not prove first exposure/),
  ).toBeTruthy();
  expect(screen.getByText(/not a validated optimal delay/)).toBeTruthy();
});

it("shows unavailable accuracy when no answers qualify", async () => {
  stubApi({
    "/me": { is_admin: true },
    "/admin/practice-outcomes": {
      ...data,
      qualifying_answers: 0,
      correct_answers: 0,
      accuracy: null,
      learners: 0,
      concepts: 0,
    },
  });
  render(await PracticeOutcomesPage());
  expect(screen.getByText(/No qualifying answers yet/)).toBeTruthy();
  expect(screen.queryByText(/0% correct/)).toBeNull();
});

it("blocks non-admins before requesting aggregate data", async () => {
  const fetch = stubApi({ "/me": { is_admin: false } });
  await expect(PracticeOutcomesPage()).rejects.toThrow("not-found");
  expect(fetch).toHaveBeenCalledTimes(1);
});
