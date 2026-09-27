"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import type { SettingsState } from "@/components/StackSettingsForm";
import { ApiError, apiPut, type ActiveStacksIn, type Me } from "@/lib/api";

/**
 * Onboarding and settings: save the ticked Stacks as the Learner's Active Stacks, then land on
 * the home screen. Unticked Stacks are deactivated and keep their progress.
 */
export async function saveActiveStacks(
  _previous: SettingsState,
  form: FormData,
): Promise<SettingsState> {
  const body: ActiveStacksIn = { stack_ids: form.getAll("stack_ids").map(String) };
  if (body.stack_ids.length === 0) return { error: "Pick at least one Stack." };
  try {
    await apiPut<Me>("/me/active-stacks", body);
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      return { error: typeof error.detail === "string" ? error.detail : "Pick at least one Stack." };
    }
    throw error;
  }
  revalidatePath("/", "layout");
  redirect("/");
}
