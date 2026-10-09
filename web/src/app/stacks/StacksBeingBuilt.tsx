import { CircleCheck, CircleDashed } from "lucide-react";
import Link from "next/link";
import { Notice } from "@/components/Notice";
import type { StackPlan } from "@/lib/api";
import { cn } from "@/lib/utils";
import { DeleteStackRequest } from "./DeleteStackRequest";

const STEPS: { key: StackPlan["step"]; label: string }[] = [
  { key: "plan", label: "Weekly plan" },
  { key: "questions", label: "Quiz setup" },
  { key: "review", label: "Admin review" },
];

/**
 * Stacks requested but not live yet, each with its three steps (the weekly plan, then the quiz
 * setup, then the Admin's review), how many Lessons have their Questions, and how to have
 * Claude build it through the connector. Its requester and the Admin may delete it.
 */
export function StacksBeingBuilt({
  plans,
  requested,
  canDelete,
  deleteAction,
}: {
  plans: StackPlan[];
  requested?: string;
  canDelete: (plan: StackPlan) => boolean;
  deleteAction: (stackId: string) => Promise<void>;
}) {
  return (
    <div className="space-y-4">
      {requested && plans.some((p) => p.stack_id === requested) && (
        <Notice tone="success" role="status">
          Requested <strong>{requested}</strong>. Now have Claude build it: the weekly plan first,
          then the quiz setup.
        </Notice>
      )}
      <ul aria-label="Stacks being built" className="space-y-4">
        {plans.map((p) => (
          <li key={p.stack_id} className="space-y-4 rounded-2xl border bg-card p-5 shadow-xs">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <p className="font-heading font-semibold">
                  {p.name} <code className="text-xs font-normal">{p.stack_id}</code>
                </p>
                <p className="text-xs text-muted-foreground">
                  Requested by {p.requested_by}
                  {p.weeks_wanted ? ` · ${p.weeks_wanted} Weeks` : ""}
                </p>
              </div>
              {canDelete(p) && (
                <DeleteStackRequest stackId={p.stack_id} name={p.name} action={deleteAction} />
              )}
            </div>
            <Steps step={p.step} />
            {p.lessons.length > 0 && (
              <p className="text-sm">
                {p.lessons_ready} of {p.lessons.length} Lessons have their Questions
                {p.thin_concepts.length > 0 &&
                  ` · ${p.thin_concepts.length} Concepts need a second Question`}
              </p>
            )}
            <p className="text-sm text-muted-foreground">{p.next_step}</p>
            {p.step !== "review" && <BuildWithClaude stackId={p.stack_id} />}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Steps({ step }: { step: StackPlan["step"] }) {
  const at = STEPS.findIndex((s) => s.key === step);
  return (
    <ol className="flex flex-wrap gap-2 text-xs font-medium" aria-label="Steps">
      {STEPS.map((s, i) => {
        const done = i < at;
        const Icon = done ? CircleCheck : CircleDashed;
        return (
          <li
            key={s.key}
            aria-current={i === at ? "step" : undefined}
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-2.5 py-1",
              done && "border-success/30 bg-success/10 text-success-foreground",
              i === at && "border-primary/30 bg-accent text-accent-foreground",
              i > at && "text-muted-foreground",
            )}
          >
            <Icon aria-hidden className="size-3.5" />
            {s.label}
            {done && <span className="sr-only"> (done)</span>}
          </li>
        );
      })}
    </ol>
  );
}

function BuildWithClaude({ stackId }: { stackId: string }) {
  return (
    <div className="space-y-1.5 rounded-xl bg-muted/60 p-3 text-sm">
      <p>
        In Claude, with the connector added (see <Link href="/settings#mcp-heading">Settings</Link>
        ), run the <strong>build_stack</strong> prompt. In Claude Code:
      </p>
      <pre className="overflow-x-auto rounded-lg bg-background p-2 text-xs">
        /mcp__chickenkiller__build_stack {stackId}
      </pre>
      <p className="text-xs text-muted-foreground">
        Or ask: &quot;Build the {stackId} Stack with the ChickenKiller connector.&quot;
      </p>
    </div>
  );
}
