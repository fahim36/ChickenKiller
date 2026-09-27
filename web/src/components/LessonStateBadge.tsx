import type { LessonState } from "@/lib/api";

const LABELS: Record<LessonState, string> = {
  completed: "Completed",
  updated: "Updated",
  unlocked: "Unlocked",
  locked: "Locked",
};

/** Whether a Lesson is Completed, Updated, Unlocked or Locked for the signed-in Learner. */
export function LessonStateBadge({ state }: { state: LessonState }) {
  return <span className={`state state-${state}`}>{LABELS[state]}</span>;
}
