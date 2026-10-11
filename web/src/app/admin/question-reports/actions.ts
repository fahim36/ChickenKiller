"use server";

import { apiPut, type QuestionReport } from "@/lib/api";

export async function associateCorrection(
  reportId: string,
  kind: "retirement" | "replacement",
  replacementId: string | null,
): Promise<QuestionReport> {
  return apiPut<QuestionReport>(
    `/admin/question-reports/${encodeURIComponent(reportId)}/correction`,
    { kind, replacement_id: replacementId },
  );
}

export async function decideReport(
  reportId: string,
  status: "accepted" | "closed",
  explanation: string,
): Promise<QuestionReport> {
  return apiPut<QuestionReport>(
    `/admin/question-reports/${encodeURIComponent(reportId)}`,
    { status, explanation },
  );
}
