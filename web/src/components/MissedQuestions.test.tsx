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
  feedback: null,
  answer: "a",
  model_answer: null,
  explanation: "`is` compares identity; `==` compares equality.",
  materials: [
    { id: "mat-docs", title: "Python docs", url: "https://docs.python.org/", type: "docs" },
  ],
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
