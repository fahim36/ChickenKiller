import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { NEW_LEARNER, ONBOARDED, stubApi } from "@/test/stubApi";
import NewStackPage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("next/cache", () => ({ revalidatePath: () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("asks what the new Stack is, and says Claude plans the Weeks before the quiz setup", async () => {
  stubApi({ "/me": ONBOARDED });

  render(await NewStackPage());

  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Add a Stack");
  for (const label of ["Name", "Id", "Summary", "Weeks"]) {
    expect(screen.getByLabelText(label, { exact: false })).toBeTruthy();
  }
  expect((screen.getByLabelText("Weeks") as HTMLInputElement).value).toBe("12");
  expect(screen.getByText(/drafts the weekly plan/)).toBeTruthy();
  expect(screen.getByText(/Then it writes the quiz setup/)).toBeTruthy();
  expect(screen.getByRole("button", { name: "Request the Stack" })).toBeTruthy();
});

it("sends a Learner who hasn't onboarded to onboarding", async () => {
  stubApi({ "/me": NEW_LEARNER });

  await expect(NewStackPage()).rejects.toThrow(
    expect.objectContaining({ digest: expect.stringContaining("/onboarding") }),
  );
});
