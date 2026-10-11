import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { stubApi } from "@/test/stubApi";
import NewReport from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("@clerk/nextjs/server", () => ({ auth: async () => ({ getToken: async () => "session-token" }) }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const path = "/stacks/mini/questions/q1/report";
const props = { searchParams: Promise.resolve({ stack_id: "mini", question_id: "q1" }) };
it("shows retirement reasons instead of inviting a report", async () => {
  stubApi({ [path]: { answered: true, retired_reason: "Invalid premise.", report: null } });
  render(await NewReport(props));
  expect(screen.getByText(/This Question was retired: Invalid premise/)).toBeTruthy();
  expect(screen.queryByRole("button")).toBeNull();
});
it("refuses reports before answering", async () => {
  stubApi({ [path]: { answered: false, retired_reason: null, report: null } });
  render(await NewReport(props));
  expect(screen.getByText(/Answer this Question before reporting/)).toBeTruthy();
  expect(screen.queryByRole("button")).toBeNull();
});
it("shows acceptance and explanation without edit controls", async () => {
  stubApi({ [path]: { answered: true, retired_reason: null, report: { status: "accepted", explanation: "A correction is being prepared." } } });
  render(await NewReport(props));
  expect(screen.getByText(/Accepted, awaiting publication/)).toBeTruthy();
  expect(screen.getByText(/A correction is being prepared/)).toBeTruthy();
  expect(screen.queryByRole("button")).toBeNull();
});
