import { Inline } from "@/components/Inline";
import { MaterialList } from "@/components/MaterialList";
import type { AnsweredQuestion } from "@/lib/api";

/**
 * The results screen's Missed Questions: for each, the Learner's answer, the correct answer
 * or Model Answer, the Explanation and the Materials. The API only sends these after the
 * answers are submitted.
 */
export function MissedQuestions({ missed }: { missed: AnsweredQuestion[] }) {
  if (missed.length === 0) return null;
  return (
    <section className="missed">
      <h2>Missed Questions</h2>
      {missed.map((q) => (
        <AnsweredQuestionDetail key={q.id} question={q} />
      ))}
    </section>
  );
}

/** One answered Question with its answer, Explanation and Materials. */
export function AnsweredQuestionDetail({ question: q }: { question: AnsweredQuestion }) {
  const promptId = `answered-${q.id}`;
  const choice = (id: string | null) => q.choices.find((c) => c.id === id)?.text ?? id ?? "";
  return (
    <article className="answered" aria-labelledby={promptId}>
      <h3 id={promptId}>
        <Inline text={q.prompt} />
      </h3>
      <p>
        <strong>Your answer:</strong>{" "}
        {q.response === null ? (
          <em>Unanswered</em>
        ) : (
          <Inline text={q.type === "written" ? q.response : choice(q.response)} />
        )}
      </p>
      {q.model_answer ? (
        <div>
          <p>
            <strong>Model Answer:</strong> <Inline text={q.model_answer.summary} />
          </p>
          <ul>
            {q.model_answer.key_points.map((point) => (
              <li key={point}>
                <Inline text={point} />
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p>
          <strong>Correct answer:</strong> <Inline text={choice(q.answer)} />
        </p>
      )}
      <p className="explanation">
        <Inline text={q.explanation} />
      </p>
      {q.materials.length > 0 && <MaterialList materials={q.materials} />}
    </article>
  );
}
