import { LocalTime } from "@/components/LocalTime";
import Link from "next/link";
import type { HomeGuidance as Guidance } from "@/lib/api";
import { Button } from "@/components/ui/button";

function actionHref(action: Guidance["action"]): string | null {
  const stack = encodeURIComponent(action.stack_id ?? "");
  const lesson = encodeURIComponent(action.lesson_id ?? "");
  switch (action.kind) {
    case "retake":
      return `/stacks/${stack}/lessons/${lesson}/quiz?attempt_id=${encodeURIComponent(action.attempt_id ?? "")}`;
    case "lesson":
      return `/stacks/${stack}/lessons/${lesson}`;
    case "concept_review":
      return `/review?stack_id=${stack}&concept_id=${encodeURIComponent(action.concept_id ?? "")}`;
    case "review":
      return "/review";
    case "complete":
      return null;
  }
}

/** Optional guidance, with observed evidence instead of a mastery estimate. */
export function HomeGuidance({ guidance }: { guidance: Guidance }) {
  const href = actionHref(guidance.action);
  return (
    <section
      aria-labelledby="next-action"
      className="mb-5 space-y-4 rounded-2xl border bg-card p-5"
    >
      <h2 id="next-action" className="font-heading text-xl font-semibold">
        Next Action
      </h2>
      <p className="text-sm text-muted-foreground">
        Optional: choose what helps you today.
      </p>
      {href ? (
        <Button asChild>
          <Link href={href}>{guidance.action.title}</Link>
        </Button>
      ) : (
        <p className="font-semibold">{guidance.action.title}</p>
      )}
      <p>{guidance.action.reason}</p>
      {guidance.weak_concepts.length > 0 && (
        <div>
          <h3 className="font-semibold">Weak Concepts</h3>
          <ul className="mt-2 space-y-3">
            {guidance.weak_concepts.map((c) => (
              <li key={`${c.stack_id}/${c.id}`}>
                <p className="font-medium">
                  {c.name} · {c.stack_name}
                </p>
                <p className="text-sm text-muted-foreground">
                  {c.recent_missed_questions} distinct Questions missed in 30
                  days
                  {c.latest_miss && (
                    <>
                      {" "}
                      · Latest miss: <LocalTime value={c.latest_miss} />
                    </>
                  )}
                </p>
                {c.lesson_id ? (
                  <Link
                    className="underline"
                    href={`/stacks/${encodeURIComponent(c.stack_id)}/lessons/${encodeURIComponent(c.lesson_id)}`}
                  >
                    {c.lesson_title}
                  </Link>
                ) : (
                  <p className="text-sm">
                    No current teaching Lesson. See your Stack&apos;s evidence.
                  </p>
                )}
                <p>
                  <Link
                    className="text-sm underline"
                    href={`/stacks/${encodeURIComponent(c.stack_id)}`}
                  >
                    Stack evidence
                  </Link>
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}
      {guidance.action.kind === "complete" && (
        <ul className="space-y-2">
          {guidance.stacks.map((stack) => (
            <li key={stack.stack_id}>
              <Link
                className="underline"
                href={`/stacks/${encodeURIComponent(stack.stack_id)}`}
              >
                Materials and Milestones · {stack.stack_name}
              </Link>
              <p className="text-sm text-muted-foreground">
                Open a Lesson for its Materials, or explore the Week&apos;s
                Milestones.
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
