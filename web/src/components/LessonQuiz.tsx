"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";
import { Inline } from "@/components/Inline";
import { MissedQuestions } from "@/components/MissedQuestions";
import { type AnswerRetakeAction, RetakeFlow } from "@/components/RetakeFlow";
import { WrittenAnswer } from "@/components/WrittenAnswer";
import type { GradingFailed, LessonQuiz as Quiz, LessonQuizResult, QuizAnswers } from "@/lib/api";

/**
 * A Lesson Quiz: multiple-choice Questions answered by picking one choice, and written ones
 * answered in a text box. Submitting sends the answers through `submitAction`; the API scores
 * them (grading written answers against their Model Answers), and this shows the score, whether
 * it met the Pass Mark, which Questions were missed, the grader's feedback on each written
 * answer and, for each Missed Question, the answers, the Explanation and the Materials.
 * Unanswered Questions are left out, so they count as missed.
 *
 * If grading fails, nothing was counted: the answers stay as they are and the Learner can
 * submit again. After a pass with Missed Questions come their Retakes (`answerRetakeAction`);
 * below the Pass Mark the Learner takes a fresh Lesson Quiz.
 */
export function LessonQuiz({
  quiz,
  stackId,
  submitAction,
  answerRetakeAction,
}: {
  quiz: Quiz;
  stackId: string;
  submitAction: (answers: QuizAnswers) => Promise<LessonQuizResult | GradingFailed>;
  answerRetakeAction: AnswerRetakeAction;
}) {
  const [answers, setAnswers] = useState<QuizAnswers>({});
  const [result, setResult] = useState<LessonQuizResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [failed, setFailed] = useState(false);
  const [gradingFailed, setGradingFailed] = useState<string | null>(null);
  const marks = new Map(result?.questions.map((q) => [q.id, q] as const));

  function answer(questionId: string, value: string) {
    setAnswers((current) => ({ ...current, [questionId]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setFailed(false);
    setGradingFailed(null);
    setSubmitting(true);
    // A blank written answer is left out, like an unpicked choice.
    const given = Object.fromEntries(
      Object.entries(answers).filter(([, value]) => value !== null && value.trim() !== ""),
    );
    try {
      const outcome = await submitAction(given);
      if ("code" in outcome) setGradingFailed(outcome.message);
      else setResult(outcome);
    } catch {
      setFailed(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <form onSubmit={submit}>
        <ol className="quiz">
          {quiz.questions.map((q) => {
            const mark = marks.get(q.id);
            return (
              <li key={q.id}>
                <fieldset disabled={result !== null}>
                  <legend>
                    <Inline text={q.prompt} />
                  </legend>
                  {q.type === "written" ? (
                    <WrittenAnswer
                      question={q}
                      value={answers[q.id] ?? ""}
                      maxLength={quiz.max_answer_chars}
                      onChange={(value) => answer(q.id, value)}
                    />
                  ) : (
                    q.choices.map((c) => (
                      <label key={c.id} className="choice">
                        <input
                          type="radio"
                          name={q.id}
                          value={c.id}
                          checked={answers[q.id] === c.id}
                          onChange={() => answer(q.id, c.id)}
                        />{" "}
                        <Inline text={c.text} />
                      </label>
                    ))
                  )}
                  {mark && (
                    <p className={mark.correct ? "mark mark-correct" : "mark mark-missed"}>
                      {mark.correct ? "Correct" : "Missed"}
                    </p>
                  )}
                  {mark?.feedback && <p className="feedback">{mark.feedback}</p>}
                </fieldset>
              </li>
            );
          })}
        </ol>

        {failed && (
          <p role="alert" className="notice notice-error">
            Couldn&apos;t submit your answers. Try again.
          </p>
        )}
        {gradingFailed && (
          <p role="alert" className="notice notice-error">
            {gradingFailed}
          </p>
        )}
        <button type="submit" disabled={submitting || result !== null}>
          {submitting ? "Grading…" : gradingFailed ? "Submit again" : "Submit answers"}
        </button>
      </form>

      {result && (
        <div role="status" className={`notice ${result.passed ? "" : "notice-error"}`}>
          <p>
            You scored {result.correct} of {result.total} ({result.percent}%).{" "}
            {outcome(result)}
          </p>
          <p>
            {!result.passed && (
              <>
                <a href={`/stacks/${stackId}/lessons/${result.lesson_id}/quiz`}>
                  Take a fresh Lesson Quiz
                </a>{" "}
                ·{" "}
              </>
            )}
            <Link href={`/stacks/${stackId}`}>Back to the Week map</Link>
          </p>
        </div>
      )}
      {result && <MissedQuestions missed={result.missed} />}
      {result && result.next_step === "retakes" && (
        <RetakeFlow
          retakes={result.retakes}
          stackId={stackId}
          maxAnswerChars={quiz.max_answer_chars}
          answerAction={answerRetakeAction}
        />
      )}
    </>
  );
}

function outcome(result: LessonQuizResult): string {
  switch (result.next_step) {
    case "completed":
      return "Passed: this Lesson is Completed and the next one is Unlocked.";
    case "retakes":
      return "Passed. Read the Explanations, then Retake each Missed Question to complete this Lesson.";
    case "fresh_quiz":
      return `Not passed: the Pass Mark is ${result.pass_mark}%. Read the Explanations, then take a fresh Lesson Quiz.`;
  }
}
