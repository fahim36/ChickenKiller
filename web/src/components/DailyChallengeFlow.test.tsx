import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type {
  AnsweredQuestion,
  ChallengeAnswerResult,
  ChallengeOutcome,
  ChallengeQuestion,
  DailyChallenge,
  GradingFailed,
} from "@/lib/api";
import { type AnswerChallengeAction, DailyChallengeFlow } from "./DailyChallengeFlow";

afterEach(cleanup);

function mc(id: string, prompt: string): ChallengeQuestion {
  return {
    id,
    type: "multiple_choice",
    prompt,
    choices: [
      { id: "a", text: "Identity" },
      { id: "b", text: "Equality" },
    ],
    retired: false,
    retired_reason: null,
    replaced_by: null,
    outcome: null,
    answered: null,
  };
}

const Q1 = mc("c001-q01", "What does `is` compare?");
const Q2 = mc("c001-q02", "What does `==` compare?");
const WRITTEN: ChallengeQuestion = {
  id: "c001-q03",
  type: "written",
  prompt: "Explain the GIL.",
  choices: [],
  retired: false,
  retired_reason: null,
  replaced_by: null,
  outcome: null,
  answered: null,
};

const NEW: DailyChallenge = {
  number: 1,
  day: "2026-09-27",
  label: "Agentic AI Engineer #1 · 27 Sep",
  status: "not_started",
  score: null,
  out_of: null,
  result_card: null,
  max_answer_chars: 4000,
  questions: [Q1, Q2, WRITTEN],
};

function details(q: ChallengeQuestion, response: string | null, feedback: string | null = null) {
  const answered: AnsweredQuestion = {
    id: q.id,
    type: q.type,
    prompt: q.prompt,
    choices: q.choices,
    response,
    selected: [],
    feedback,
    answer: q.type === "written" ? null : "a",
    answers: [],
    model_answer:
      q.type === "written" ? { summary: "One thread at a time.", key_points: ["One lock"] } : null,
    explanation: `Because of ${q.id}.`,
    materials: [],
    sources: [
      {
        url: `https://docs.example.com/${q.id}`,
        title: `Source for ${q.id}`,
        publisher: "Example",
        accessed: "2026-09-26",
        claim: "The claim.",
      },
    ],
  };
  return answered;
}

/** `challenge` with each of `outcomes` (by Question ID) as its first tries. */
function played(
  outcomes: Record<string, ChallengeOutcome>,
  extra: Partial<DailyChallenge> = {},
): DailyChallenge {
  return {
    ...NEW,
    status: "in_progress",
    ...extra,
    questions: NEW.questions.map((q) =>
      q.id in outcomes
        ? { ...q, outcome: outcomes[q.id], answered: details(q, q.type === "written" ? "Mine." : "a") }
        : q,
    ),
  };
}

function result(
  q: ChallengeQuestion,
  outcome: ChallengeOutcome,
  challenge: DailyChallenge,
  { counted = true, response = "a", feedback = null as string | null } = {},
): ChallengeAnswerResult {
  return { counted, outcome, question: details(q, response, feedback), challenge };
}

function renderFlow(answerAction: AnswerChallengeAction, challenge: DailyChallenge = NEW) {
  render(
    <DailyChallengeFlow
      stackId="agentic-ai-engineer"
      challenge={challenge}
      answerAction={answerAction}
    />,
  );
}

function submit() {
  fireEvent.click(screen.getByRole("button", { name: "Submit answer" }));
}

it("asks one Question at a time, the first not answered yet", () => {
  renderFlow(vi.fn(), played({ "c001-q01": "correct" }));

  expect(screen.getByText("Question 2 of 3")).toBeTruthy();
  expect(screen.getByRole("group", { name: "What does == compare?" })).toBeTruthy();
  expect(screen.queryByText("What does is compare?")).toBeNull();
});

it("says only the first answer counts", () => {
  renderFlow(vi.fn());

  expect(screen.getByText(/Only your first answer to each Question counts/)).toBeTruthy();
});

it("shows the result, the Explanation and every Source with its link after each answer", async () => {
  const answerAction = vi.fn(async () => result(Q1, "correct", played({ "c001-q01": "correct" })));
  renderFlow(answerAction);

  fireEvent.click(screen.getByRole("radio", { name: "Identity" }));
  submit();

  expect(await screen.findByText("Correct")).toBeTruthy();
  expect(answerAction).toHaveBeenCalledWith("c001-q01", "a");
  expect(screen.getByText("Because of c001-q01.")).toBeTruthy();
  const link = within(screen.getByRole("list", { name: "Sources" })).getByRole("link", {
    name: "Source for c001-q01",
  });
  expect(link.getAttribute("href")).toBe("https://docs.example.com/c001-q01");

  fireEvent.click(screen.getByRole("button", { name: "Next Question" }));
  expect(screen.getByText("Question 2 of 3")).toBeTruthy();
});

it("says so after a wrong answer, with the correct answer", async () => {
  renderFlow(vi.fn(async () => result(Q1, "wrong", played({ "c001-q01": "wrong" }), { response: "b" })));

  fireEvent.click(screen.getByRole("radio", { name: "Equality" }));
  submit();

  expect(await screen.findByText(/Not quite/)).toBeTruthy();
  expect(screen.getByText("Because of c001-q01.")).toBeTruthy();
});

it("shows Grading… while a written answer is graded, then the grader's feedback", async () => {
  let resolve: (r: ChallengeAnswerResult) => void = () => {};
  const answerAction = vi.fn(
    () => new Promise<ChallengeAnswerResult | GradingFailed>((r) => (resolve = r)),
  );
  renderFlow(answerAction, played({ "c001-q01": "correct", "c001-q02": "correct" }));

  fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "Mine." } });
  submit();

  const button = await screen.findByRole("button", { name: "Grading…" });
  expect(button.hasAttribute("disabled")).toBe(true);
  resolve(
    result(WRITTEN, "wrong", played({ "c001-q01": "correct", "c001-q02": "correct", "c001-q03": "wrong" }, { status: "finished", score: 2, out_of: 3 }), {
      response: "Mine.",
      feedback: "Missing: one lock.",
    }),
  );
  expect(await screen.findByText("Missing: one lock.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "See your score" }));
  expect(screen.getByText("Played: 2/3")).toBeTruthy();
});

it("when grading fails, marks the Question ungraded and lets the Learner resubmit for feedback only", async () => {
  const finished = played(
    { "c001-q01": "correct", "c001-q02": "correct", "c001-q03": "ungraded" },
    { status: "finished", score: 2, out_of: 3 },
  );
  const answerAction = vi
    .fn<AnswerChallengeAction>()
    .mockResolvedValueOnce(result(WRITTEN, "ungraded", finished, { response: "Mine." }))
    .mockResolvedValueOnce(
      result(WRITTEN, "correct", finished, {
        counted: false,
        response: "Mine.",
        feedback: "Covers every key point.",
      }),
    );
  renderFlow(answerAction, played({ "c001-q01": "correct", "c001-q02": "correct" }));

  fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "Mine." } });
  submit();

  expect(await screen.findByText(/couldn't be graded, so it earns no point/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Resubmit for feedback" }));
  expect(await screen.findByText("Covers every key point.")).toBeTruthy();
  expect(answerAction).toHaveBeenLastCalledWith("c001-q03", "Mine.");
  expect(screen.getByText(/Feedback only: this answer earns no point/)).toBeTruthy();
});

it("offers to send a resubmission again when it can't be graded either", async () => {
  const finished = played(
    { "c001-q01": "correct", "c001-q02": "correct", "c001-q03": "ungraded" },
    { status: "finished", score: 2, out_of: 3 },
  );
  renderFlow(
    vi.fn(async () => ({ code: "grading_failed", message: "Nothing was counted: submit again." }) as const),
    finished,
  );

  fireEvent.click(screen.getByRole("button", { name: "Resubmit for feedback" }));

  expect(await screen.findByText("Nothing was counted: submit again.")).toBeTruthy();
});

it("sums up a finished Challenge and replays it for learning only", async () => {
  const finished = played(
    { "c001-q01": "correct", "c001-q02": "wrong", "c001-q03": "correct" },
    { status: "finished", score: 2, out_of: 3 },
  );
  const answerAction = vi.fn(async () =>
    result(Q1, "wrong", finished, { counted: false, response: "b" }),
  );
  renderFlow(answerAction, finished);

  expect(screen.getByText("Played: 2/3")).toBeTruthy();
  expect(screen.getAllByText("Wrong").length).toBe(1);
  fireEvent.click(screen.getByRole("button", { name: "Replay" }));

  expect(screen.getByText("Replay · Question 1 of 3")).toBeTruthy();
  fireEvent.click(screen.getByRole("radio", { name: "Equality" }));
  submit();
  expect(await screen.findByText(/Not quite/)).toBeTruthy();
  expect(screen.getByText(/A replay changes no score, Streak or Missed Question/)).toBeTruthy();
});

it("offers the Result Card of a finished Challenge, and none before", () => {
  const card = "Agentic AI Engineer #1 · 27 Sep · 2/3 ✅❌✅";
  const finished = played(
    { "c001-q01": "correct", "c001-q02": "wrong", "c001-q03": "correct" },
    { status: "finished", score: 2, out_of: 3, result_card: card },
  );
  renderFlow(vi.fn(), finished);

  expect(screen.getByText(card)).toBeTruthy();
  expect(screen.getByRole("button", { name: "Copy Result Card" })).toBeTruthy();
  cleanup();

  renderFlow(vi.fn());
  expect(screen.queryByRole("button", { name: "Copy Result Card" })).toBeNull();
});

it("skips a Retired Question, which can't be answered", () => {
  const challenge: DailyChallenge = {
    ...played({ "c001-q01": "correct", "c001-q02": "correct" }, { status: "finished", score: 2, out_of: 2 }),
  };
  challenge.questions[2] = { ...WRITTEN, retired: true, retired_reason: "Out of date." };
  renderFlow(vi.fn(), challenge);

  expect(screen.getByText("Played: 2/2")).toBeTruthy();
  expect(
    screen.getByText(/Retired: Out of date\. It can't be answered and isn't scored\./),
  ).toBeTruthy();
  expect(screen.queryByRole("group")).toBeNull();
});

it("links a Retired Question to the Challenge that asks its replacement", () => {
  const challenge = played({ "c001-q01": "correct" }, { status: "finished", score: 1, out_of: 1 });
  challenge.questions[1] = {
    ...Q2,
    retired: true,
    retired_reason: "Out of date.",
    replaced_by: {
      question_id: "c009-q01",
      challenge_number: 9,
      challenge_label: "Agentic AI Engineer #9 · 5 Oct",
    },
  };
  challenge.questions[2] = {
    ...WRITTEN,
    retired: true,
    retired_reason: "Wrong.",
    replaced_by: { question_id: "c010-q01", challenge_number: null, challenge_label: null },
  };
  renderFlow(vi.fn(), challenge);

  expect(
    screen.getByRole("link", { name: "Agentic AI Engineer #9 · 5 Oct" }).getAttribute("href"),
  ).toBe("/stacks/agentic-ai-engineer/archive/9");
  const unlinked = screen.getByText(/Retired: Wrong\..*A newer Question replaces it\./);
  expect(within(unlinked).queryByRole("link")).toBeNull();
});

const SELECT: ChallengeQuestion = {
  id: "c001-q04",
  type: "multiple_select",
  prompt: "Which hold the GIL? Select all that apply.",
  choices: [
    { id: "a", text: "CPython" },
    { id: "b", text: "Jython" },
    { id: "c", text: "PyPy" },
    { id: "d", text: "IronPython" },
  ],
  retired: false,
  retired_reason: null,
  replaced_by: null,
  outcome: null,
  answered: null,
};

it("answers a multiple-select Question by ticking every choice that applies", async () => {
  const challenge: DailyChallenge = { ...NEW, questions: [SELECT] };
  const answered: AnsweredQuestion = {
    ...details(SELECT, "a,b"),
    answer: null,
    selected: ["a", "b"],
    answers: ["a", "c"],
  };
  const answerAction = vi.fn<AnswerChallengeAction>(async () => ({
    counted: true,
    outcome: "wrong",
    question: answered,
    challenge: { ...challenge, status: "finished", score: 0, out_of: 1 },
  }));
  renderFlow(answerAction, challenge);

  const group = screen.getByRole("group", { name: /Which hold the GIL/ });
  expect(within(group).getByText("Select all that apply.")).toBeTruthy();
  expect(within(group).queryAllByRole("radio")).toHaveLength(0);
  expect(screen.getByRole("button", { name: "Submit answer" }).hasAttribute("disabled")).toBe(true);
  fireEvent.click(within(group).getByRole("checkbox", { name: "Jython" }));
  fireEvent.click(within(group).getByRole("checkbox", { name: "CPython" }));
  submit();

  await vi.waitFor(() => expect(answerAction).toHaveBeenCalledWith("c001-q04", ["a", "b"]));
  expect(await screen.findByText(/Not quite/)).toBeTruthy();
  expect(
    within(screen.getByRole("list", { name: "Correct answers" }))
      .getAllByRole("listitem")
      .map((li) => li.textContent),
  ).toEqual(["CPython", "PyPy"]);
});
