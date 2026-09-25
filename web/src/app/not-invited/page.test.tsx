import { cleanup, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";
import NotInvitedPage from "./page";

vi.mock("@clerk/nextjs", () => ({
  SignOutButton: ({ children }: { children: ReactNode }) => children,
}));

afterEach(cleanup);

it("tells a person who wasn't invited why they can't get in, and lets them switch account", () => {
  render(<NotInvitedPage />);

  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(
    "You haven't been invited yet",
  );
  expect(screen.getByText(/ask the Admin for an invitation/i)).toBeTruthy();
  expect(screen.getByRole("button", { name: "Sign in with another account" })).toBeTruthy();
});
