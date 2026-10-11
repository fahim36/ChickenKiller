"use server";

import { api, apiPost, apiDelete } from "@/lib/api";
import type {
  InterviewSession,
  InterviewOperation,
  InterviewRecording,
} from "./types";

export async function uploadInterviewAudio(
  id: string,
  promptId: string,
  recordingId: string,
  form: FormData,
) {
  const file = form.get("audio");
  if (!(file instanceof File) || file.size > 3000000)
    throw Error("Unsupported recording size");
  return apiPost<InterviewRecording>(
    `/me/interviews/${encodeURIComponent(id)}/audio`,
    {
      recording_id: recordingId,
      prompt_id: promptId,
      mime: file.type.split(";")[0],
      data: Buffer.from(await file.arrayBuffer()).toString("base64"),
    },
  );
}
export async function transcribeInterviewAudio(
  id: string,
  recordingId: string,
  operationId: string,
) {
  return apiPost<InterviewRecording>(
    `/me/interviews/${encodeURIComponent(id)}/audio/${encodeURIComponent(recordingId)}/transcribe`,
    { operation_id: operationId },
  );
}
export async function loadInterviewAudio(id: string, recordingId: string) {
  return api<{ mime: string; data: string }>(
    `/me/interviews/${encodeURIComponent(id)}/audio/${encodeURIComponent(recordingId)}`,
  );
}
export async function cancelInterviewAudio(id: string, recordingId: string) {
  await apiDelete(
    `/me/interviews/${encodeURIComponent(id)}/audio/${encodeURIComponent(recordingId)}`,
  );
}
export async function confirmInterviewTranscript(
  id: string,
  recordingId: string,
  promptId: string,
  text: string,
) {
  return apiPost<InterviewSession>(
    `/me/interviews/${encodeURIComponent(id)}/responses`,
    { recording_id: recordingId, prompt_id: promptId, text, confirmed: true },
  );
}

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

export async function openInterviewTurn(
  id: string,
  parentId: string,
  kind: "follow_up" | "retry",
  followUpId?: string,
) {
  return apiPost<InterviewSession>(
    `/me/interviews/${encodeURIComponent(id)}/turns`,
    {
      parent_id: parentId,
      kind,
      follow_up_id: followUpId ?? null,
    },
  );
}
