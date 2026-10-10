import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type {
  AnsweredQuestion,
  GradingFailed,
  LessonQuiz as Quiz,
  LessonQuizResult,
  QuizAnswers,
  RetakeResult,
} from "@/lib/api";
import { LessonQuiz } from "./LessonQuiz";

// Four multiple-choice Questions (1 to 4), then two written ones (5 and 6).
const quiz: Quiz = {
  attempt_id: "3f1c7a52-0000-4000-8000-000000000001",
  lesson_id: "w01-l01",
  version: "v2026-09-26",
  pass_mark: 80,
  max_answer_chars: 4000,
  questions: [
    ...[1, 2, 3, 4].map((n) => ({
      id: `w01-l01-q0${n}`,
      type: "multiple_choice" as const,
      prompt: `Question ${n}?`,
      choices: [
        { id: "a", text: `Right ${n}` },
        { id: "b", text: `Wrong ${n}` },
      ],
    })),
    ...[5, 6].map((n) => ({
      id: `w01-l01-q0${n}`,
      type: "written" as const,
      prompt: `Question ${n}?`,
      choices: [],
    })),
  ],
};

function missed(n: number): AnsweredQuestion {
  const written = quiz.questions[n - 1].type === "written";
  return {
    ...quiz.questions[n - 1],
    response: written ? "Not sure." : "b",
    selected: [],
    feedback: written ? "Missing: the loop." : null,
    answer: written ? null : "a",
    answers: [],
    model_answer: written ? { summary: "Agents loop.", key_points: ["loop", "tools"] } : null,
    explanation: `Because of ${n}.`,
    materials: [],
    sources: [],
  };
}

/** The API's result with the first `correct` Questions right and the rest missed. */
function result(correct: number): LessonQuizResult {
  const passed = correct >= 5;
  const missedNumbers = [1, 2, 3, 4, 5, 6].slice(correct);
  return {
    attempt_id: quiz.attempt_id,
    lesson_id: "w01-l01",
    correct,
    total: 6,
    percent: Math.round((correct / 6) * 100),
    passed,
    pass_mark: 80,
    questions: quiz.questions.map((q, i) => ({ id: q.id, correct: i < correct, feedback: null })),
    missed: missedNumbers.map(missed),
    next_step: !passed ? "fresh_quiz" : correct === 6 ? "completed" : "retakes",
    lesson_completed: correct === 6,
    retakes: passed
      ? missedNumbers.map((n) => ({
          id: `retake-${n}`,
          missed_question_id: `w01-l01-q0${n}`,
          question: { ...quiz.questions[0], id: "w01-l01-q09", prompt: `Sibling of ${n}?` },
        }))
      : [],
  };
}

afterEach(cleanup);

type Submit = (answers: QuizAnswers) => Promise<LessonQuizResult | GradingFailed>;
type AnswerRetake = (
  retakeId: string,
  answer: string | string[] | null,
) => Promise<RetakeResult | GradingFailed>;

function renderQuiz(submitAction: Submit, answerRetakeAction: AnswerRetake = vi.fn()) {
  render(
    <LessonQuiz
      quiz={quiz}
      stackId="agentic-ai-engineer"
      submitAction={submitAction}
      answerRetakeAction={answerRetakeAction}
    />,
  );
}

const question = (n: number) => screen.getByRole("group", { name: new RegExp(`Question ${n}\\?`) });

function choose(n: number, text: string) {
  fireEvent.click(within(question(n)).getByRole("radio", { name: text }));
}

function write(n: number, text: string) {
  fireEvent.change(within(question(n)).getByRole("textbox", { name: "Your answer" }), {
    target: { value: text },
  });
}

const submitButton = () => screen.getByRole("button", { name: /Submit/ });

it("shows the multiple-choice Questions with their choices and the written ones with a box", () => {
  renderQuiz(vi.fn());

  expect(screen.getAllByRole("group")).toHaveLength(6);
  const first = question(1);
  expect(within(first).getAllByRole("radio").map((r) => r.getAttribute("value"))).toEqual([
    "a",
    "b",
  ]);
  expect(within(first).getByText("Right 1")).toBeTruthy();
  expect(within(question(5)).queryAllByRole("radio")).toHaveLength(0);
  const box = within(question(5)).getByRole("textbox", { name: "Your answer" });
  expect(box.getAttribute("maxlength")).toBe("4000");
});

it("submits the chosen and written answers, leaving unanswered Questions out", async () => {
  const submitAction = vi.fn(async () => result(5));
  renderQuiz(submitAction);

  choose(1, "Right 1");
  choose(2, "Wrong 2");
  choose(2, "Right 2");
  write(5, "An agent calls tools in a loop.");
  write(6, "   ");
  fireEvent.click(submitButton());

  await vi.waitFor(() =>
    expect(submitAction).toHaveBeenCalledWith({
      "w01-l01-q01": "a",
      "w01-l01-q02": "a",
      "w01-l01-q05": "An agent calls tools in a loop.",
    }),
  );
});

it("shows a pass with no misses as a Completed Lesson with a way back to the Week map", async () => {
  renderQuiz(vi.fn(async () => result(6)));

  fireEvent.click(submitButton());

  const status = await screen.findByRole("status");
  expect(status.textContent).toContain("6 of 6 (100%)");
  expect(status.textContent).toContain("Passed: this Lesson is Completed");
  expect(
    screen.getByRole("link", { name: "Back to the Week map" }).getAttribute("href"),
  ).toBe("/stacks/agentic-ai-engineer");
  expect(submitButton().hasAttribute("disabled")).toBe(true);
});

it("shows a fail against the Pass Mark and offers a fresh quiz", async () => {
  renderQuiz(vi.fn(async () => result(4)));

  fireEvent.click(submitButton());

  const status = await screen.findByRole("status");
  expect(status.textContent).toContain("4 of 6 (67%)");
  expect(status.textContent).toContain("Not passed: the Pass Mark is 80%");
  expect(screen.queryByRole("heading", { name: "Retakes" })).toBeNull();
  expect(
    screen.getByRole("link", { name: "Take a fresh Lesson Quiz" }).getAttribute("href"),
  ).toBe("/stacks/agentic-ai-engineer/lessons/w01-l01/quiz");
});

it("marks which Questions were right and which were missed", async () => {
  renderQuiz(vi.fn(async () => result(4)));

  fireEvent.click(submitButton());
  await screen.findByRole("status");

  const marks = quiz.questions.map(
    (_, i) => within(question(i + 1)).getByText(/^(Correct|Missed)$/).textContent,
  );
  expect(marks).toEqual(["Correct", "Correct", "Correct", "Correct", "Missed", "Missed"]);
});

it("shows the grader's feedback on each written answer", async () => {
  const graded = result(5);
  graded.questions[4].feedback = "Covers every key point.";
  graded.questions[5].feedback = "Missing: the loop.";
  renderQuiz(vi.fn(async () => graded));

  fireEvent.click(submitButton());
  await screen.findByRole("status");

  expect(within(question(5)).getByText("Correct")).toBeTruthy();
  expect(within(question(5)).getByText("Covers every key point.")).toBeTruthy();
  expect(within(question(6)).getByText("Missed")).toBeTruthy();
  expect(within(question(6)).getByText("Missing: the loop.")).toBeTruthy();
});

it("says nothing was counted when grading fails, and lets the Learner submit again", async () => {
  const failure: GradingFailed = {
    code: "grading_failed",
    message: "Your written answers couldn't be graded just now. Nothing was counted.",
  };
  const submitAction = vi.fn<Submit>().mockResolvedValueOnce(failure).mockResolvedValueOnce(result(6));
  renderQuiz(submitAction);
  write(5, "My answer.");

  fireEvent.click(submitButton());

  expect((await screen.findByRole("alert")).textContent).toBe(failure.message);
  expect(screen.queryByRole("status")).toBeNull();
  expect(submitButton().textContent).toBe("Submit again");
  const box = within(question(5)).getByRole("textbox", { name: "Your answer" });
  expect((box as HTMLTextAreaElement).value).toBe("My answer.");

  fireEvent.click(submitButton());

  expect((await screen.findByRole("status")).textContent).toContain("6 of 6 (100%)");
  expect(submitAction).toHaveBeenLastCalledWith({ "w01-l01-q05": "My answer." });
  expect(screen.queryByRole("alert")).toBeNull();
});

it("says so and lets the Learner try again when submitting fails", async () => {
  const submitAction = vi
    .fn<Submit>()
    .mockRejectedValueOnce(new Error("HTTP 500"))
    .mockResolvedValueOnce(result(6));
  renderQuiz(submitAction);

  fireEvent.click(submitButton());

  expect((await screen.findByRole("alert")).textContent).toBe(
    "Couldn't submit your answers. Try again.",
  );
  fireEvent.click(submitButton());
  expect((await screen.findByRole("status")).textContent).toContain("6 of 6 (100%)");
});

it("after submitting shows each Missed Question's Explanation", async () => {
  renderQuiz(vi.fn(async () => result(4)));

  fireEvent.click(submitButton());

  expect(await screen.findByRole("heading", { name: "Missed Questions" })).toBeTruthy();
  const explained = screen.getAllByRole("article").map((a) => a.querySelector("h3")?.textContent);
  expect(explained).toEqual(["Question 5?", "Question 6?"]);
  expect(screen.getByText("Because of 5.")).toBeTruthy();
  const written = screen.getAllByRole("article")[0];
  expect(within(written).getByText("Agents loop.")).toBeTruthy();
});

it("shows each Missed Question's Sources and Materials on the results screen", async () => {
  const withSources: LessonQuizResult = {
    ...result(5),
    missed: [
      {
        ...missed(6),
        sources: [
          {
            url: "https://example.com/agents",
            title: "Building agents",
            publisher: "Example",
            accessed: "2026-09-20",
            claim: "An agent calls tools in a loop.",
          },
        ],
        materials: [
          { id: "mat-course", title: "Agents course", url: "https://example.com/course", type: "free" },
        ],
      },
    ],
  };
  renderQuiz(vi.fn(async () => withSources));

  fireEvent.click(submitButton());

  const explained = await screen.findByRole("article", { name: "Question 6?" });
  expect(within(explained).getByRole("list", { name: "Sources" }).textContent).toBe(
    "Building agents · Example: An agent calls tools in a loop.",
  );
  expect(within(explained).getByRole("link", { name: "Building agents" }).getAttribute("href")).toBe(
    "https://example.com/agents",
  );
  expect(within(explained).getByRole("link", { name: "Agents course" }).getAttribute("href")).toBe(
    "https://example.com/course",
  );
});

it("a pass with a Missed Question goes on to its Retake, and a correct one completes the Lesson", async () => {
  const answerRetake = vi.fn<AnswerRetake>(async () => ({
    retake_id: "retake-6",
    correct: true,
    question: { ...missed(1), id: "w01-l01-q09", response: "a" },
    next_question: null,
    pending: 0,
    lesson_completed: true,
  }));
  renderQuiz(vi.fn(async () => result(5)), answerRetake);

  fireEvent.click(submitButton());

  expect((await screen.findByRole("status")).textContent).toContain(
    "Retake each Missed Question to complete this Lesson",
  );
  const sibling = screen.getByRole("group", { name: "Sibling of 6?" });
  fireEvent.click(within(sibling).getByRole("radio", { name: "Right 1" }));
  fireEvent.click(screen.getByRole("button", { name: "Submit Retake" }));

  await vi.waitFor(() => expect(answerRetake).toHaveBeenCalledWith("retake-6", "a", "w01-l01-q09"));
  expect(
    (await screen.findByText(/Every Retake is resolved/)).textContent,
  ).toContain("this Lesson is Completed and the next one is Unlocked");
});

it("answers a multiple-select Question with every choice ticked, in choice order", async () => {
  const withSelect: Quiz = {
    ...quiz,
    questions: [
      ...quiz.questions.slice(0, 4),
      {
        id: "w01-l01-q07",
        type: "multiple_select",
        prompt: "Question 7? Select all that apply.",
        choices: ["a", "b", "c", "d"].map((id) => ({ id, text: `Choice ${id}` })),
      },
    ],
  };
  const submitAction = vi.fn(async () => result(5));
  render(
    <LessonQuiz
      quiz={withSelect}
      stackId="agentic-ai-engineer"
      submitAction={submitAction}
      answerRetakeAction={vi.fn()}
    />,
  );

  const group = question(7);
  fireEvent.click(within(group).getByRole("checkbox", { name: "Choice c" }));
  fireEvent.click(within(group).getByRole("checkbox", { name: "Choice b" }));
  fireEvent.click(within(group).getByRole("checkbox", { name: "Choice a" }));
  fireEvent.click(within(group).getByRole("checkbox", { name: "Choice b" }));
  expect(screen.getByText("1 of 5 answered")).toBeTruthy();
  fireEvent.click(submitButton());

  await vi.waitFor(() => expect(submitAction).toHaveBeenCalledWith({ "w01-l01-q07": ["a", "c"] }));
});
