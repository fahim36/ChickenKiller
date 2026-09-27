import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import SignInUnavailablePage from "./page";

afterEach(cleanup);

it("says sign-in can't be checked right now, and lets the person try again", () => {
  render(<SignInUnavailablePage />);

  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(
    "Sign-in can't be checked right now",
  );
  expect(
    screen.getByRole("link", { name: "Try again" }).getAttribute("href"),
  ).toBe("/");
  expect(screen.getByText("CLERK_ISSUER")).toBeTruthy();
});
