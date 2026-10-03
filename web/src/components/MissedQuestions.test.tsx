import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import type { AnsweredQuestion } from "@/lib/api";
import { AnsweredQuestionDetail, MissedQuestions } from "./MissedQuestions";

afterEach(cleanup);

const wrong: AnsweredQuestion = {
  id: "w01-l01-q01",
  type: "multiple_choice",
  prompt: "What does `is` compare?",
  choices: [
    { id: "a", text: "Identity" },
    { id: "b", text: "Equality" },
  ],
  response: "b",
  selected: [],
  feedback: null,
  answer: "a",
  answers: [],
  model_answer: null,
  explanation: "`is` compares identity; `==` compares equality.",
  materials: [
    { id: "mat-docs", title: "Python docs", url: "https://docs.python.org/", type: "docs" },
  ],
  sources: [],
};

const unanswered: AnsweredQuestion = {
  ...wrong,
  id: "w01-l01-q02",
  prompt: "Which is mutable?",
  choices: [
    { id: "a", text: "list" },
    { id: "b", text: "tuple" },
  ],
  response: null,
  explanation: "Lists can change.",
  materials: [],
};

const written: AnsweredQuestion = {
  ...wrong,
  id: "w01-l01-q07",
  type: "written",
  prompt: "Explain the mutable default argument trap.",
  choices: [],
  response: "Defaults are fine.",
  feedback: "Missing: evaluated once.",
  answer: null,
  model_answer: { summary: "Defaults are evaluated once.", key_points: ["once", "shared"] },
  explanation: "The default object is shared between calls.",
  materials: [],
};

function detail(prompt: string) {
  return screen.getByRole("article", { name: prompt });
}

it("shows each Missed Question with the Learner's answer, the correct one and the Explanation", () => {
  render(<MissedQuestions missed={[wrong, unanswered]} />);

  expect(screen.getByRole("heading", { name: "Missed Questions" })).toBeTruthy();
  const first = detail("What does is compare?");
  expect(within(first).getByText("Your answer:").parentElement?.textContent).toBe(
    "Your answer: Equality",
  );
  expect(within(first).getByText("Correct answer:").parentElement?.textContent).toBe(
    "Correct answer: Identity",
  );
  expect(within(first).getByText(/compares identity/).textContent).toBe(
    "is compares identity; == compares equality.",
  );
  expect(
    within(detail("Which is mutable?")).getByText("Your answer:").parentElement?.textContent,
  ).toBe("Your answer: Unanswered");
});

it("links a Missed Question's Materials", () => {
  render(<MissedQuestions missed={[wrong]} />);

  const link = within(detail("What does is compare?")).getByRole("link", { name: "Python docs" });
  expect(link.getAttribute("href")).toBe("https://docs.python.org/");
});

it("shows a written Question's feedback and Model Answer instead of a correct choice", () => {
  render(<AnsweredQuestionDetail question={written} />);

  const article = detail("Explain the mutable default argument trap.");
  expect(within(article).getByText("Your answer:").parentElement?.textContent).toBe(
    "Your answer: Defaults are fine.",
  );
  expect(within(article).getByText("Missing: evaluated once.")).toBeTruthy();
  expect(within(article).getByText("Defaults are evaluated once.")).toBeTruthy();
  expect(within(article).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
    "once",
    "shared",
  ]);
});

it("shows nothing when no Question was missed", () => {
  const { container } = render(<MissedQuestions missed={[]} />);

  expect(container.textContent).toBe("");
});

const multipleSelect: AnsweredQuestion = {
  ...wrong,
  id: "w01-l01-q09",
  type: "multiple_select",
  prompt: "Which are immutable? Select all that apply.",
  choices: [
    { id: "a", text: "tuple" },
    { id: "b", text: "list" },
    { id: "c", text: "frozenset" },
    { id: "d", text: "dict" },
  ],
  response: "a,b",
  selected: ["a", "b"],
  answer: null,
  answers: ["a", "c"],
  explanation: "Tuples and frozensets can't change.",
  materials: [],
};

it("shows a multiple-select Question's ticks, each marked, against every correct choice", () => {
  render(<AnsweredQuestionDetail question={multipleSelect} />);

  const yours = screen.getByRole("list", { name: "Your answer" });
  expect(within(yours).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
    "tuple",
    "list (not a correct choice)",
  ]);
  const correct = screen.getByRole("list", { name: "Correct answers" });
  expect(within(correct).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
    "tuple",
    "frozenset",
  ]);
  expect(screen.getByText("Tuples and frozensets can't change.")).toBeTruthy();
});

it("shows no correct answers box when every right choice and only those were ticked", () => {
  render(
    <AnsweredQuestionDetail
      question={{ ...multipleSelect, response: "a,c", selected: ["a", "c"] }}
    />,
  );

  expect(screen.queryByRole("list", { name: "Correct answers" })).toBeNull();
  expect(screen.getByRole("list", { name: "Your answer" })).toBeTruthy();
});

it("shows an unanswered multiple-select Question as unanswered", () => {
  render(<AnsweredQuestionDetail question={{ ...multipleSelect, response: null, selected: [] }} />);

  expect(screen.getByText("Unanswered")).toBeTruthy();
  expect(screen.queryByRole("list", { name: "Your answer" })).toBeNull();
});
