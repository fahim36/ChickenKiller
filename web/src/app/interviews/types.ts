export interface InterviewPrompt {
  id: string;
  concept: string;
  lesson: string;
  scenario: string;
  rubric: string[];
  misconceptions: string[];
}
export interface InterviewSession {
  id: string;
  stack_id: string;
  expires_at: string;
  prompts: InterviewPrompt[];
  responses: Record<string, string | null>;
  operations?: InterviewOperation[];
}
export interface InterviewOperation {
  id: string;
  prompt_id: string;
  state: string;
  feedback: {
    criteria: { dimension: string; finding: string; quote: string | null }[];
    uncertainty: string;
    next_steps: string[];
    follow_up: string | null;
  } | null;
}
export interface Topics {
  topics: { concept: string; id: string; scenario: string }[];
  lesson_id: string | null;
  message: string | null;
}
