"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import type { SettingsState } from "@/components/StackSettingsForm";
import { ApiError, apiPut, type Me, type Settings } from "@/lib/api";

/** Onboarding and settings: save the Active Stack and time zone, then land on that Stack. */
export async function saveSettings(_previous: SettingsState, form: FormData): Promise<SettingsState> {
  const settings: Settings = {
    active_stack_id: String(form.get("active_stack_id") ?? ""),
    time_zone: String(form.get("time_zone") ?? "").trim(),
  };
  try {
    await apiPut<Me>("/me/settings", settings);
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      return { error: validationMessage(error.detail, settings.time_zone) };
    }
    throw error;
  }
  revalidatePath("/", "layout");
  redirect(`/stacks/${encodeURIComponent(settings.active_stack_id)}`);
}

function validationMessage(detail: unknown, timeZone: string): string {
  if (typeof detail === "string") return detail;
  const aboutTimeZone =
    Array.isArray(detail) &&
    detail.some((d: { loc?: unknown[] }) => d.loc?.includes("time_zone") ?? false);
  if (aboutTimeZone) {
    return `“${timeZone}” isn't a time zone. Pick one from the list, such as Asia/Dhaka.`;
  }
  return "Choose a Stack and a time zone.";
}
