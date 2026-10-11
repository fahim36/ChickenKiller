"use server";

import { apiPut, type QuestionReport, type ReportCategory } from "@/lib/api";

export async function saveReport(stackId: string, questionId: string, category: ReportCategory, note: string): Promise<QuestionReport> {
  return apiPut<QuestionReport>(`/stacks/${encodeURIComponent(stackId)}/questions/${encodeURIComponent(questionId)}/report`, { category, note: note.trim() || null });
}
