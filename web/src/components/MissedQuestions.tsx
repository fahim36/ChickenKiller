import { BookOpenCheck, ExternalLink, Lightbulb } from "lucide-react";
import { Inline } from "@/components/Inline";
import { MaterialList } from "@/components/MaterialList";
import type { AnsweredQuestion } from "@/lib/api";

/**
 * The results screen's Missed Questions: for each, the Learner's answer, the grader's
 * feedback (written), the correct answer or Model Answer, the Explanation, the Sources and the
 * Materials. The API only sends these after the answers are submitted.
 */
export function MissedQuestions({ missed }: { missed: AnsweredQuestion[] }) {
  if (missed.length === 0) return null;
  return (
    <section className="mt-10 space-y-4">
      <h2 className="font-heading text-lg font-semibold tracking-tight">Missed Questions</h2>
      {missed.map((q) => (
        <AnsweredQuestionDetail key={q.id} question={q} />
      ))}
    </section>
  );
}

/** One answered Question with its answer, Explanation, Sources and Materials. */
export function AnsweredQuestionDetail({ question: q }: { question: AnsweredQuestion }) {
  const promptId = `answered-${q.id}`;
  const choice = (id: string | null) => q.choices.find((c) => c.id === id)?.text ?? id ?? "";
  return (
    <article
      className="space-y-4 rounded-2xl border bg-card p-5 text-sm leading-relaxed shadow-xs sm:p-6 sm:text-base"
      aria-labelledby={promptId}
    >
      <h3 id={promptId} className="font-heading text-base font-semibold sm:text-lg">
        <Inline text={q.prompt} />
      </h3>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-3">
          <p>
            <strong className="block text-xs font-semibold tracking-wide text-destructive uppercase">
              Your answer:
            </strong>{" "}
            {q.response === null ? (
              <em className="text-muted-foreground">Unanswered</em>
            ) : (
              <Inline text={q.type === "written" ? q.response : choice(q.response)} />
            )}
          </p>
        </div>
        {q.model_answer ? (
          <div className="rounded-xl border border-success/25 bg-success/5 p-3">
            <p>
              <strong className="block text-xs font-semibold tracking-wide text-success-foreground uppercase">
                Model Answer:
              </strong>{" "}
              <Inline text={q.model_answer.summary} />
            </p>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {q.model_answer.key_points.map((point) => (
                <li key={point}>
                  <Inline text={point} />
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="rounded-xl border border-success/25 bg-success/5 p-3">
            <p>
              <strong className="block text-xs font-semibold tracking-wide text-success-foreground uppercase">
                Correct answer:
              </strong>{" "}
              <Inline text={choice(q.answer)} />
            </p>
          </div>
        )}
      </div>

      {q.feedback && (
        <p className="rounded-xl bg-muted px-3 py-2 text-sm text-muted-foreground">{q.feedback}</p>
      )}

      <div className="flex gap-3 rounded-xl bg-accent/50 p-3 text-accent-foreground">
        <Lightbulb aria-hidden className="mt-0.5 size-4 shrink-0" />
        <p>
          <Inline text={q.explanation} />
        </p>
      </div>

      {q.sources.length > 0 && (
        <div className="space-y-2">
          <p className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            <BookOpenCheck aria-hidden className="size-3.5" /> Sources
          </p>
          <ul className="space-y-2 text-sm" aria-label="Sources">
            {q.sources.map((s) => (
              <li key={s.url} className="text-muted-foreground">
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 font-medium text-foreground underline-offset-4 hover:text-primary hover:underline"
                >
                  {s.title}
                  <ExternalLink aria-hidden className="size-3" />
                </a>{" "}
                · {s.publisher}: <Inline text={s.claim} />
              </li>
            ))}
          </ul>
        </div>
      )}
      {q.materials.length > 0 && <MaterialList materials={q.materials} />}
    </article>
  );
}
