import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import type { HomeGuidance as Guidance } from "@/lib/api";
import { HomeGuidance } from "./HomeGuidance";

afterEach(cleanup);
const guidance: Guidance = {
  action: {
    kind: "concept_review",
    title: "Practise aliases",
    reason: "Two distinct misses; due Review is available.",
    stack_id: "python",
    concept_id: "aliases",
    lesson_id: null,
    attempt_id: null,
  },
  weak_concepts: [
    {
      id: "aliases",
      name: "Aliasing",
      stack_id: "python",
      stack_name: "Python",
      status: "weak",
      recent_missed_questions: 2,
      latest_miss: "2026-10-11T10:00:00Z",
      active_questions: 4,
      recovery_days: 0,
      recovery_questions: 0,
      lesson_id: "names",
      lesson_title: "Names",
    },
  ],
  stacks: [{ stack_id: "python", stack_name: "Python" }],
};

it("shows one optional action, private evidence and targeted due Review", () => {
  render(<HomeGuidance guidance={guidance} />);
  expect(screen.getByRole("region", { name: "Next Action" })).toBeTruthy();
  expect(screen.getByText(/Optional/)).toBeTruthy();
  expect(
    screen.getByRole("link", { name: "Practise aliases" }).getAttribute("href"),
  ).toBe("/review?stack_id=python&concept_id=aliases");
  expect(screen.getByText(/2 distinct Questions missed/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "Names" }).getAttribute("href")).toBe(
    "/stacks/python/lessons/names",
  );
});

it("shows resources for caught-up learners and handles missing teaching Lessons", () => {
  render(
    <HomeGuidance
      guidance={{
        ...guidance,
        action: {
          ...guidance.action,
          kind: "complete",
          title: "You're caught up",
        },
        weak_concepts: [
          { ...guidance.weak_concepts[0], lesson_id: null, lesson_title: null },
        ],
      }}
    />,
  );
  expect(
    screen
      .getByRole("link", { name: /Materials and Milestones/ })
      .getAttribute("href"),
  ).toBe("/stacks/python");
  expect(screen.getByText(/No current teaching Lesson/)).toBeTruthy();
});

it("links pending Retakes to the existing quiz flow", () => {
  render(
    <HomeGuidance
      guidance={{
        ...guidance,
        action: {
          ...guidance.action,
          kind: "retake",
          title: "Finish Retake",
          lesson_id: "names",
          attempt_id: "passed-attempt",
        },
      }}
    />,
  );
  expect(
    screen.getByRole("link", { name: "Finish Retake" }).getAttribute("href"),
  ).toBe("/stacks/python/lessons/names/quiz?attempt_id=passed-attempt");
});
