import { notFound } from "next/navigation";
import { connection } from "next/server";
import { api } from "@/lib/api";
import { PlacementPractice } from "../PlacementPractice";
import type { PlacementAttempt } from "../types";

export default async function PlacementPage({
  params,
}: PageProps<"/placements/[attemptId]">) {
  await connection();
  const { attemptId } = await params;
  const attempt = await api<PlacementAttempt>(
    `/me/placements/${encodeURIComponent(attemptId)}`,
  );
  if (!attempt) notFound();
  return (
    <main className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-semibold">
        Placement Quiz · {attempt.week_id}
      </h1>
      <PlacementPractice initial={attempt} />
    </main>
  );
}
