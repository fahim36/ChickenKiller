import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

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

/**
 * A Lesson's state for the signed-in Learner. Only the Unlocked Lesson's quiz can be started;
 * every Lesson can be read.
 */
export type LessonState = "completed" | "unlocked" | "locked";

export interface LessonSummary {
  id: string;
  title: string;
  minutes: number;
  state: LessonState;
}

export interface Milestone {
  id: string;
  title: string;
  kind: "build" | "job-hunt";
  minutes: number;
  /** Whether the signed-in Learner has ticked it off. Never affects unlocking. */
  ticked: boolean;
}

export interface MilestoneTick {
  id: string;
  ticked: boolean;
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
  state: LessonState;
  previous_lesson_id: string | null;
  next_lesson_id: string | null;
}

/** A Question as the Learner sees it while answering: never its answer or Explanation. */
export interface QuizQuestion {
  id: string;
  type: "multiple_choice";
  prompt: string;
  choices: { id: string; text: string }[];
}

/** A started (or resumed) Lesson Quiz. */
export interface LessonQuiz {
  attempt_id: string;
  lesson_id: string;
  version: string;
  /** As a percentage. */
  pass_mark: number;
  questions: QuizQuestion[];
}

/** The Learner's answers by Question ID. A Question left out is unanswered, so missed. */
export type QuizAnswers = Record<string, string | null>;

/**
 * A Question after the Learner answered it: their response, the correct answer or Model
 * Answer, the Explanation and the Materials. Only sent once the answer is submitted.
 */
export interface AnsweredQuestion {
  id: string;
  type: "multiple_choice" | "written";
  prompt: string;
  /** Empty for a written Question. */
  choices: { id: string; text: string }[];
  /** The Learner's choice ID or written answer; null when left unanswered. */
  response: string | null;
  /** The correct choice ID, for multiple choice. */
  answer: string | null;
  model_answer: { summary: string; key_points: string[] } | null;
  explanation: string;
  materials: Material[];
}

/** A pending Retake: a sibling Question on the Missed Question's Concept. */
export interface Retake {
  id: string;
  missed_question_id: string;
  question: QuizQuestion;
}

/**
 * What follows a submitted Lesson Quiz: "completed" (passed with no Missed Question),
 * "retakes" (passed with Missed Questions: the Lesson completes once every Retake is
 * correct) or "fresh_quiz" (below the Pass Mark).
 */
export type NextStep = "completed" | "retakes" | "fresh_quiz";

/** A submitted Lesson Quiz, scored by the API. */
export interface LessonQuizResult {
  attempt_id: string;
  lesson_id: string;
  correct: number;
  total: number;
  percent: number;
  /** Met the Pass Mark. The Lesson is Completed only once every Retake is correct too. */
  passed: boolean;
  pass_mark: number;
  questions: { id: string; correct: boolean }[];
  /** Each Missed Question, in the order asked. */
  missed: AnsweredQuestion[];
  next_step: NextStep;
  lesson_completed: boolean;
  /** Pending Retakes, when `next_step` is "retakes". */
  retakes: Retake[];
}

/** A passed attempt's pending Retakes. */
export interface Retakes {
  attempt_id: string;
  lesson_id: string;
  lesson_completed: boolean;
  retakes: Retake[];
}

/** An answered Retake. Wrong: its Explanation and `next_question`, another sibling to try. */
export interface RetakeResult {
  retake_id: string;
  correct: boolean;
  question: AnsweredQuestion;
  next_question: QuizQuestion | null;
  /** Retakes still waiting for a correct answer. At 0 the Lesson is Completed. */
  pending: number;
  lesson_completed: boolean;
}

export interface ActiveStack {
  id: string;
  name: string;
  started_at: string;
}

export interface Me {
  email: string;
  is_admin: boolean;
  /** True until the Learner has picked an Active Stack and a time zone. */
  needs_onboarding: boolean;
  active_stack: ActiveStack | null;
  /** An IANA name, such as Asia/Dhaka. */
  time_zone: string | null;
}

/** What onboarding sets, and settings change. */
export interface Settings {
  active_stack_id: string;
  time_zone: string;
}

export interface Invitation {
  email: string;
  invited_at: string;
}

const API_URL = process.env.API_URL ?? "http://localhost:8000";

/** A non-2xx answer from the API. `detail` is FastAPI's error detail. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: unknown,
    request: string,
  ) {
    super(typeof detail === "string" ? detail : `${request} failed: HTTP ${status}`);
  }
}

/**
 * Call the API as the signed-in person: every request carries their Clerk session token.
 * A person who signed in but was never invited is sent to /not-invited, and a Learner who
 * hasn't picked an Active Stack yet is sent to /onboarding.
 */
async function request(method: string, path: string, body?: unknown): Promise<Response> {
  const { getToken } = await auth();
  const token = await getToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (res.ok || res.status === 404) return res;

  const detail = await res
    .json()
    .then((json: { detail?: unknown }) => json.detail)
    .catch(() => null);
  if (res.status === 403 && hasCode(detail, "not_invited")) redirect("/not-invited");
  if (res.status === 409 && hasCode(detail, "onboarding_needed")) redirect("/onboarding");
  throw new ApiError(res.status, detail, `${method} ${path}`);
}

function hasCode(detail: unknown, code: string): boolean {
  return (
    typeof detail === "object" && detail !== null && (detail as { code?: unknown }).code === code
  );
}

/** GET from the API. Resolves null on 404 so pages can call notFound(). */
export async function api<T>(path: string): Promise<T | null> {
  const res = await request("GET", path);
  if (res.status === 404) return null;
  return res.json() as Promise<T>;
}

/** POST JSON to the API. Throws ApiError on any error status, including 404. */
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await request("POST", path, body);
  if (res.status === 404) throw new ApiError(404, "Not found", `POST ${path}`);
  return res.json() as Promise<T>;
}

/** PUT JSON to the API. Throws ApiError on any error status, including 404. */
export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await request("PUT", path, body);
  if (res.status === 404) throw new ApiError(404, "Not found", `PUT ${path}`);
  return res.json() as Promise<T>;
}
