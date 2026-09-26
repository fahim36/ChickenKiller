import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ResultCard } from "./ResultCard";

const CARD = "Agentic AI Engineer #1 · 27 Sep · 2/3 ✅❌⬜";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows the Result Card and what each mark means", () => {
  render(<ResultCard text={CARD} />);

  expect(screen.getByText(CARD)).toBeTruthy();
  expect(screen.getByText(/✅ correct/)).toBeTruthy();
  expect(screen.getByText(/⬜ ungraded/)).toBeTruthy();
});

it("copies the Result Card as text", async () => {
  const writeText = vi.fn(async () => {});
  vi.stubGlobal("navigator", { clipboard: { writeText } });
  render(<ResultCard text={CARD} />);

  fireEvent.click(screen.getByRole("button", { name: "Copy Result Card" }));

  expect(await screen.findByText("Copied")).toBeTruthy();
  expect(writeText).toHaveBeenCalledWith(CARD);
});

it("falls back to copying the selected text without the clipboard API", async () => {
  vi.stubGlobal("navigator", {});
  const execCommand = vi.fn(() => true);
  document.execCommand = execCommand;
  render(<ResultCard text={CARD} />);

  fireEvent.click(screen.getByRole("button", { name: "Copy Result Card" }));

  expect(await screen.findByText("Copied")).toBeTruthy();
  expect(execCommand).toHaveBeenCalledWith("copy");
});

it("asks the Learner to copy it themselves when copying fails", async () => {
  vi.stubGlobal("navigator", { clipboard: { writeText: async () => Promise.reject(new Error()) } });
  document.execCommand = vi.fn(() => false);
  render(<ResultCard text={CARD} />);

  fireEvent.click(screen.getByRole("button", { name: "Copy Result Card" }));

  expect(await screen.findByText(/Couldn't copy/)).toBeTruthy();
});
