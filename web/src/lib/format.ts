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

/** Planned time for a Week: its Lessons plus its Milestones. */
export function weekMinutes(week: Pick<Week, "lessons" | "milestones">): number {
  return [...week.lessons, ...week.milestones].reduce((sum, x) => sum + x.minutes, 0);
}
