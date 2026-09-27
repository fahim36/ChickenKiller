import { cleanup, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";
import SignInFailedPage from "./page";

vi.mock("@clerk/nextjs", () => ({
  SignOutButton: ({ children }: { children: ReactNode }) => children,
}));

afterEach(cleanup);

it("explains a sign-in the API couldn't verify, offers to sign in again, and hints the Admin", () => {
  render(<SignInFailedPage />);

  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(
    "Your sign-in couldn't be verified",
  );
  expect(
    screen.getByRole("button", { name: "Sign out and sign in again" }),
  ).toBeTruthy();
  expect(screen.getByText(/Customize session token/)).toBeTruthy();
  expect(screen.getByText(/primary_email_address/)).toBeTruthy();
});
