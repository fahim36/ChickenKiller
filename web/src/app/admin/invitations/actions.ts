"use server";

import { revalidatePath } from "next/cache";
import { ApiError, apiPost, type Invitation } from "@/lib/api";
import type { InviteState } from "./InviteForm";

// The API checks that the caller is the Admin; this action only forwards their session token.
export async function invite(_previous: InviteState, form: FormData): Promise<InviteState> {
  const email = String(form.get("email") ?? "").trim();
  try {
    await apiPost<Invitation>("/invitations", { email });
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      return { ok: false, message: "Enter an email address, such as name@example.com." };
    }
    if (error instanceof ApiError && error.status < 500) {
      return { ok: false, message: error.message };
    }
    throw error;
  }
  revalidatePath("/admin/invitations");
  return { ok: true, message: `Invited ${email}. They can sign in now.` };
}
