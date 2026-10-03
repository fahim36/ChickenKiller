import { describe, expect, it } from "vitest";
import { isAnswered, submittedAnswer, toggleChoice } from "./answers";
import type { Answer } from "./api";

describe("isAnswered", () => {
  const cases: [Answer | undefined, boolean][] = [
    ["a", true],
    [["a"], true],
    ["An answer.", true],
    [[], false],
    ["   ", false],
    [null, false],
    [undefined, false],
  ];

  it.each(cases)("%j -> %s", (answer, expected) => {
    expect(isAnswered(answer)).toBe(expected);
  });
});

describe("submittedAnswer", () => {
  it("sends no ticks or a blank written answer as unanswered", () => {
    expect(submittedAnswer([])).toBeNull();
    expect(submittedAnswer("  ")).toBeNull();
    expect(submittedAnswer(["a", "c"])).toEqual(["a", "c"]);
    expect(submittedAnswer("b")).toBe("b");
  });
});

describe("toggleChoice", () => {
  const ids = ["a", "b", "c", "d"];

  it("ticks and unticks, keeping the choices' order", () => {
    expect(toggleChoice([], "c", ids)).toEqual(["c"]);
    expect(toggleChoice(["c"], "a", ids)).toEqual(["a", "c"]);
    expect(toggleChoice(["a", "c"], "a", ids)).toEqual(["c"]);
  });
});
