import { describe, expect, it } from "vitest";
import { formatMinutes, formatTimeLeft, materialLabel, weekMinutes } from "./format";

describe("formatMinutes", () => {
  it.each([
    [45, "45 min"],
    [60, "1 h"],
    [150, "2 h 30 min"],
  ])("%i -> %s", (minutes, expected) => {
    expect(formatMinutes(minutes)).toBe(expected);
  });
});

describe("weekMinutes", () => {
  it("adds Lessons and Milestones", () => {
    const week = {
      lessons: [
        {
          id: "w01-l01",
          title: "a",
          minutes: 60,
          state: "unlocked" as const,
          waiting_for_review: false,
        },
      ],
      milestones: [
        { id: "w01-m01", title: "b", kind: "build" as const, minutes: 90, ticked: false },
      ],
    };
    expect(weekMinutes(week)).toBe(150);
  });
});

describe("formatTimeLeft", () => {
  const now = new Date("2026-09-26T04:00:00Z");

  it.each([
    ["2026-09-26T06:00:00Z", "2 h"],
    ["2026-09-26T04:00:01Z", "1 min"],
    ["2026-09-26T03:00:00Z", "0 min"],
  ])("until %s -> %s", (until, expected) => {
    expect(formatTimeLeft(new Date(until), now)).toBe(expected);
  });
});

describe("materialLabel", () => {
  it("names each Material type", () => {
    expect(materialLabel("docs")).toBe("Official docs");
    expect(materialLabel("paid")).toBe("Paid course");
  });
});
