// Types mirror the FastAPI response models in api/app/schemas.py.

export type MaterialType =
  | "docs"
  | "free"
  | "video"
  | "book"
  | "paper"
  | "tool"
  | "paid"
  | "platform";

export interface StackSummary {
  id: string;
  name: string;
  summary: string;
  version: string;
}

export interface Material {
  id: string;
  title: string;
  url: string;
  type: MaterialType;
}

export interface LessonSummary {
  id: string;
  title: string;
  minutes: number;
}

export interface Milestone {
  id: string;
  title: string;
  kind: "build" | "job-hunt";
  minutes: number;
}

export interface Week {
  id: string;
  number: number;
  title: string;
  goal: string;
  deliverable: string;
  lessons: LessonSummary[];
  milestones: Milestone[];
}

export interface Syllabus extends StackSummary {
  weeks: Week[];
}

export interface Lesson {
  id: string;
  stack_id: string;
  week: { id: string; number: number; title: string };
  title: string;
  topics: string[];
  exercise: string | null;
  minutes: number;
  materials: Material[];
  previous_lesson_id: string | null;
  next_lesson_id: string | null;
}

const API_URL = process.env.API_URL ?? "http://localhost:8000";

/** GET from the API. Resolves null on 404 so pages can call notFound(). */
export async function api<T>(path: string): Promise<T | null> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`GET ${path} failed: HTTP ${res.status}`);
  return res.json() as Promise<T>;
}
