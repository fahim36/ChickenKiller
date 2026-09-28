"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import type { SettingsState } from "@/components/StackSettingsForm";
import {
  ApiError,
  apiDelete,
  apiPost,
  apiPut,
  type ActiveStacksIn,
  type Me,
  type StackPlan,
  type StackRequestIn,
} from "@/lib/api";

/**
 * Onboarding and the Stacks screen: save the ticked Stacks as the Learner's Active Stacks, then land on
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
      return {
        error: typeof error.detail === "string" ? error.detail : "Pick at least one Stack.",
      };
    }
    throw error;
  }
  revalidatePath("/", "layout");
  redirect("/");
}

export type StackRequestState = { error: string; values: Record<string, string> } | null;

/**
 * The Add a Stack screen: request a new Stack, then land on the Stacks screen, where it is
 * listed with how far Claude has built it.
 */
export async function requestStack(
  _previous: StackRequestState,
  form: FormData,
): Promise<StackRequestState> {
  const text = (name: string) => String(form.get(name) ?? "").trim();
  const values = Object.fromEntries(
    ["id", "name", "summary", "audience", "weeks", "notes"].map((n) => [n, text(n)]),
  );
  const body: StackRequestIn = {
    id: values.id.toLowerCase(),
    name: values.name,
    summary: values.summary,
    audience: values.audience,
    weeks: Number(values.weeks || 12),
    notes: values.notes,
  };
  if (!body.id || !body.name || !body.summary) {
    return { error: "Give the Stack an id, a name and a one-line summary.", values };
  }
  try {
    await apiPost<StackPlan>("/stack-requests", body);
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      return {
        error: typeof error.detail === "string" ? error.detail : "Check the fields and try again.",
        values,
      };
    }
    throw error;
  }
  revalidatePath("/stacks");
  redirect(`/stacks?requested=${encodeURIComponent(body.id)}#building`);
}

/** Delete a Stack being built, with all its drafts: its requester or the Admin only. */
export async function deleteStackRequest(stackId: string): Promise<void> {
  await apiDelete(`/stack-requests/${encodeURIComponent(stackId)}`);
  revalidatePath("/stacks");
}
