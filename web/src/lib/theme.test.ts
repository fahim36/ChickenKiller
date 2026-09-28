import { expect, it } from "vitest";
import { parseTheme } from "./theme";

it("is Light on a first visit, and keeps a Theme the Learner picked", () => {
  expect(parseTheme(undefined)).toBe("light");
  expect(parseTheme("nonsense")).toBe("light");
  expect(parseTheme("dark")).toBe("dark");
  expect(parseTheme("system")).toBe("system");
});
