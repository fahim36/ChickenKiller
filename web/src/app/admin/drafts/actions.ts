"use server";

import { revalidatePath } from "next/cache";
import { apiPut, type Draft } from "@/lib/api";

// The API checks that the caller is the Admin; this action only forwards their session token.
export async function decideDraft(id: number, status: "accepted" | "rejected"): Promise<void> {
  await apiPut<Draft>(`/admin/drafts/${id}`, { status });
  revalidatePath("/admin/drafts");
}
