export interface InterviewPrompt {
  id: string;
  concept: string;
  lesson: string;
  scenario: string;
  rubric: string[];
  misconceptions: string[];
  follow_ups?: { id: string; scenario: string; rubric: string[] }[];
  parent_id?: string;
  kind?: "follow_up" | "retry";
  seconds?: 45 | 60;
}
export interface InterviewSession {
  id: string;
  stack_id: string;
  expires_at: string;
  prompts: InterviewPrompt[];
  responses: Record<string, string | null>;
  operations?: InterviewOperation[];
  recordings?: InterviewRecording[];
  turns?: InterviewPrompt[];
  practice_state?: string;
  ai_enabled?: boolean;
}
export interface InterviewRecording {
  id: string;
  prompt_id: string;
  expires_at: string;
  transcript: string | null;
  state?: string;
}
export interface InterviewOperation {
  id: string;
  prompt_id: string;
  state: string;
  kind?: "feedback" | "transcription";
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
