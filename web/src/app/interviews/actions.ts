"use server";

import { apiPost, apiDelete } from "@/lib/api";
import type { InterviewSession, InterviewOperation } from "./types";

export async function requestInterviewFeedback(
  id: string,
  operationId: string,
  promptId: string,
  confirmed: boolean,
) {
  return apiPost<InterviewOperation>(
    `/me/interviews/${encodeURIComponent(id)}/feedback`,
    { operation_id: operationId, prompt_id: promptId, confirmed },
  );
}

export async function startInterview(stack: string, concepts: string[]) {
  return apiPost<InterviewSession>(
    `/stacks/${encodeURIComponent(stack)}/interviews`,
    { concepts },
  );
}
export async function saveInterviewResponse(
  id: string,
  promptId: string,
  text: string | null,
) {
  return apiPost<InterviewSession>(
    `/me/interviews/${encodeURIComponent(id)}/responses`,
    { prompt_id: promptId, text },
  );
}
export async function deleteInterview(id: string) {
  await apiDelete(`/me/interviews/${encodeURIComponent(id)}`);
}
