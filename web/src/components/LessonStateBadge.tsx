import { CircleCheck, Lock, LockOpen, Sparkles } from "lucide-react";
import type { LessonState } from "@/lib/api";
import { cn } from "@/lib/utils";

const LABELS: Record<LessonState, string> = {
  completed: "Completed",
  updated: "Updated",
  unlocked: "Unlocked",
  locked: "Locked",
};

const STYLES: Record<LessonState, string> = {
  completed: "bg-success/12 text-success-foreground ring-success/25",
  updated: "bg-warning/15 text-warning-foreground ring-warning/30",
  unlocked: "bg-primary text-primary-foreground ring-primary",
  locked: "bg-muted text-muted-foreground ring-border",
};

const ICONS = { completed: CircleCheck, updated: Sparkles, unlocked: LockOpen, locked: Lock };

/** Whether a Lesson is Completed, Updated, Unlocked or Locked for the signed-in Learner. */
export function LessonStateBadge({ state, className }: { state: LessonState; className?: string }) {
  const Icon = ICONS[state];
  return (
    <span
      className={cn(
        "inline-flex h-6 shrink-0 items-center gap-1 rounded-full px-2 text-xs font-medium ring-1 ring-inset",
        STYLES[state],
        className,
      )}
    >
      <Icon aria-hidden className="size-3.5" />
      <span>{LABELS[state]}</span>
    </span>
  );
}
