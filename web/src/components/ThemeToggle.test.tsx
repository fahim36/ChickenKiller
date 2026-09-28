import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { ThemeToggle } from "./ThemeToggle";

afterEach(() => {
  cleanup();
  delete document.documentElement.dataset.theme;
  document.cookie = "theme=; path=/; max-age=0";
});

it("starts on the Learner's saved theme", () => {
  render(<ThemeToggle initial="dark" />);

  expect(
    screen.getByRole("radio", { name: "Dark" }).getAttribute("aria-checked"),
  ).toBe("true");
});

it("applies a picked theme at once and remembers it in a cookie", () => {
  render(<ThemeToggle initial="system" />);

  fireEvent.click(screen.getByRole("radio", { name: "Light" }));

  expect(document.documentElement.dataset.theme).toBe("light");
  expect(document.cookie).toContain("theme=light");
  expect(
    screen.getByRole("radio", { name: "Light" }).getAttribute("aria-checked"),
  ).toBe("true");
});

it("follows the system setting again when System is picked", () => {
  document.documentElement.dataset.theme = "dark";
  render(<ThemeToggle initial="dark" />);

  fireEvent.click(screen.getByRole("radio", { name: "System" }));

  expect(document.documentElement.dataset.theme).toBeUndefined();
  expect(document.cookie).toContain("theme=system");
});
