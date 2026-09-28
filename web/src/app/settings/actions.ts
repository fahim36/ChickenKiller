"use server";

import { revalidatePath } from "next/cache";
import { ApiError, apiDelete, apiPost, apiPut, type Grading, type NewAccessToken } from "@/lib/api";

export type KeyState = { ok: boolean; message: string } | null;
export type TokenState = { ok: true; token: NewAccessToken } | { ok: false; message: string } | null;

/** Save (or replace) the Learner's Gemini key for grading. The API stores it encrypted. */
export async function saveGradingKey(_previous: KeyState, form: FormData): Promise<KeyState> {
  const apiKey = String(form.get("api_key") ?? "").trim();
  const model = String(form.get("model") ?? "").trim();
  if (!apiKey) return { ok: false, message: "Paste your API key first." };
  try {
    await apiPut<Grading>("/me/grading-key", {
      provider: "gemini",
      api_key: apiKey,
      model: model || null,
    });
  } catch (error) {
    if (error instanceof ApiError && (error.status === 422 || error.status === 503)) {
      return { ok: false, message: typeof error.detail === "string" ? error.detail : error.message };
    }
    throw error;
  }
  revalidatePath("/settings");
  return { ok: true, message: "Saved. Your written answers are now graded with your key." };
}

export async function removeGradingKey(): Promise<void> {
  await apiDelete<Grading>("/me/grading-key");
  revalidatePath("/settings");
}

/** A new personal access token for the MCP connector: shown to the Learner once. */
export async function createAccessToken(
  _previous: TokenState,
  form: FormData,
): Promise<TokenState> {
  const name = String(form.get("name") ?? "").trim() || "Claude";
  try {
    const token = await apiPost<NewAccessToken>("/me/access-tokens", { name });
    revalidatePath("/settings");
    return { ok: true, token };
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      return { ok: false, message: typeof error.detail === "string" ? error.detail : error.message };
    }
    throw error;
  }
}

export async function revokeAccessToken(id: number): Promise<void> {
  await apiDelete(`/me/access-tokens/${id}`);
  revalidatePath("/settings");
}
