import { expect, it } from "vitest";
import { formatLocalTime } from "./LocalTime";

it("moves an instant across the local midnight boundary", () => {
  expect(formatLocalTime("2026-10-11T20:30:00Z", false, "Asia/Dhaka")).toBe(
    "12 Oct 2026, 02:30",
  );
  expect(
    formatLocalTime("2026-10-11T20:30:00Z", false, "America/Los_Angeles"),
  ).toBe("11 Oct 2026, 13:30");
});

it("shows a scheduled day at its local release date", () => {
  expect(formatLocalTime("2026-10-12", true, "America/Los_Angeles")).toBe(
    "11 Oct 2026",
  );
});
