import { describe, expect, it } from "vitest";
import { formatMinutes, materialLabel, weekMinutes } from "./format";

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
      lessons: [{ id: "w01-l01", title: "a", minutes: 60 }],
      milestones: [{ id: "w01-m01", title: "b", kind: "build" as const, minutes: 90 }],
    };
    expect(weekMinutes(week)).toBe(150);
  });
});

describe("materialLabel", () => {
  it("names each Material type", () => {
    expect(materialLabel("docs")).toBe("Official docs");
    expect(materialLabel("paid")).toBe("Paid course");
  });
});
