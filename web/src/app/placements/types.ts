export interface PlacementAttempt {
  id: string;
  stack_id: string;
  week_id: string;
  state: "open" | "submitted" | "cancelled" | "abandoned";
  reason: string | null;
  questions: {
    id: string;
    lesson: string;
    type: "multiple_choice" | "multiple_select";
    prompt: string;
    choices: { id: string; text: string }[];
    answer?: string;
    answers?: string[];
    explanation?: string;
    sources?: { url: string; title: string }[];
  }[];
  responses: Record<string, string | string[] | null>;
  result: null | {
    passed: boolean;
    correct: number;
    total: number;
    lessons: {
      lesson: string;
      correct: number;
      total: number;
      passed: boolean;
    }[];
    correct_questions: Record<string, boolean>;
  };
}

export interface PlacementEligibility {
  available: boolean;
  reason: string | null;
  attempt_id: string | null;
  week_id: string;
}
