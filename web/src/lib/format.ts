import type { MaterialType, Week } from "./api";

const MATERIAL_LABELS: Record<MaterialType, string> = {
  docs: "Official docs",
  free: "Free course",
  video: "Video",
  book: "Book",
  paper: "Paper",
  tool: "Tool",
  paid: "Paid course",
  platform: "Platform",
};

export function materialLabel(type: MaterialType): string {
  return MATERIAL_LABELS[type] ?? type;
}

export function formatMinutes(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m} min`;
  return m === 0 ? `${h} h` : `${h} h ${m} min`;
}

/** Time left until `until`, in whole minutes rounded up ("1 h 5 min"); "0 min" once past. */
export function formatTimeLeft(until: Date, now: Date): string {
  return formatMinutes(Math.max(0, Math.ceil((until.getTime() - now.getTime()) / 60_000)));
}

/** The time of day of `at` in UTC, where every Day turns (ADR-0005): "14:05 UTC". */
export function formatClock(at: Date): string {
  const clock = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "UTC",
  }).format(at);
  return `${clock} UTC`;
}

/** Planned time for a Week: its Lessons plus its Milestones. */
export function weekMinutes(week: Pick<Week, "lessons" | "milestones">): number {
  return [...week.lessons, ...week.milestones].reduce((sum, x) => sum + x.minutes, 0);
}
