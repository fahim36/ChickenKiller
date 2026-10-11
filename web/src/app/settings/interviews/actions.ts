"use server";
import { apiPut } from "@/lib/api";
import type { InterviewSettings } from "./InterviewSettingsForm";

export async function updateInterviewSettings(settings: InterviewSettings) {
  return apiPut<InterviewSettings>("/me/interview-settings", settings);
}
