import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { ConceptEvidence } from "./ConceptEvidence";
import type { StackEvidence } from "@/lib/api";

afterEach(cleanup);

it("shows distinct misses and recovery evidence with a teaching Lesson link", () => {
  render(<ConceptEvidence evidence={{
    stack_id: "mini-stack", as_of: "2026-10-03", concepts: [{
      id: "concept-a", name: "Names and objects", active_questions: 2,
      lesson_id: "w01-l01", lesson_title: "Python names", status: "weak",
      recent_missed_questions: 2, latest_miss: "2026-10-02T23:59:00Z",
      recovery_days: 1, recovery_questions: 1,
    }],
  }} />);
  expect(screen.getByRole("region", { name: "Concept evidence" })).toBeTruthy();
  expect(screen.getByText("Weak Concept")).toBeTruthy();
  expect(screen.getByText(/2 distinct Questions missed/)).toBeTruthy();
  expect(screen.getByText(/1 of 3 UTC Days/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "Read Python names" }).getAttribute("href"))
    .toBe("/stacks/mini-stack/lessons/w01-l01");
});

it("distinguishes expiration, recovery and insufficient evidence without inventing Lesson links", () => {
  const evidence: StackEvidence = {
    stack_id: "mini-stack", as_of: "2026-10-03", concepts: [
      { id: "expired", name: "Expired example", active_questions: 2, lesson_id: null, lesson_title: null,
        status: "expired", recent_missed_questions: 0, latest_miss: "2026-09-01T10:00:00Z", recovery_days: 0, recovery_questions: 0 },
      { id: "recovered", name: "Recovered example", active_questions: 4, lesson_id: null, lesson_title: null,
        status: "recovered", recent_missed_questions: 2, latest_miss: "2026-10-01T10:00:00Z", recovery_days: 3, recovery_questions: 2 },
      { id: "sparse", name: "Sparse example", active_questions: 1, lesson_id: null, lesson_title: null,
        status: "insufficient", recent_missed_questions: 1, latest_miss: "2026-10-02T10:00:00Z", recovery_days: 0, recovery_questions: 0 },
    ],
  };
  render(<ConceptEvidence evidence={evidence} />);
  expect(screen.getByText("No recent evidence")).toBeTruthy();
  expect(screen.getByText("Recovery rule met")).toBeTruthy();
  expect(screen.getByText("Not enough evidence")).toBeTruthy();
  expect(screen.getByText(/does not indicate recovery/)).toBeTruthy();
  expect(screen.queryByRole("link")).toBeNull();
});
