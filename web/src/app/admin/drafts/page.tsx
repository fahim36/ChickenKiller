import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Notice } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { api, type Draft, type Me } from "@/lib/api";
import { cn } from "@/lib/utils";
import { decideDraft } from "./actions";
import { DraftActions } from "./DraftActions";

const dateFormat = new Intl.DateTimeFormat("en-GB", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "UTC",
});

const STATUS_TONE: Record<Draft["status"], string> = {
  pending: "bg-warning/15 text-warning-foreground",
  accepted: "bg-success/15 text-success-foreground",
  rejected: "bg-muted text-muted-foreground",
  exported: "bg-primary/10 text-primary",
};

// Admin only. The API refuses non-Admins too; this check just keeps the screen out of sight.
export default async function DraftsPage() {
  await connection();
  const me = await api<Me>("/me");
  if (!me?.is_admin) notFound();
  const drafts = (await api<Draft[]>("/admin/drafts")) ?? [];

  return (
    <main className="mx-auto max-w-3xl">
      <PageHeader
        crumbs={
          <>
            <Link href="/settings">Settings</Link> ·{" "}
            <Link href="/admin/challenges">Upcoming Challenges</Link>
          </>
        }
        title="Drafts"
        description={
          <p>
            Questions and Daily Challenges proposed through the Claude connector, and new Stacks
            being built, each by its author. Accepting changes nothing yet: run{" "}
            <code>content-export-drafts</code>, then merge the files with /update-syllabus or
            /write-challenges and commit. A new Stack&apos;s accepted weekly plan and Questions
            are written as its first version: run <code>content-check</code> and{" "}
            <code>content-import</code>.
          </p>
        }
      />

      {drafts.length === 0 ? (
        <Notice>No drafts yet.</Notice>
      ) : (
        <ul className="space-y-4" aria-label="Drafts">
          {drafts.map((d) => (
            <li key={d.id} className="space-y-3 rounded-2xl border bg-card p-5 shadow-xs">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <p className="font-heading font-semibold">
                    {draftTitle(d)}{" "}
                    · {d.stack_id}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    #{d.id} by {d.author_email} · {dateFormat.format(new Date(d.created_at))} UTC
                  </p>
                </div>
                <span
                  className={cn(
                    "rounded-full px-2.5 py-1 text-xs font-semibold",
                    STATUS_TONE[d.status],
                  )}
                >
                  {d.status}
                </span>
              </div>
              {d.note && <p className="text-sm">{d.note}</p>}
              <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                {(d.payload.questions ?? []).map((q) =>
                  typeof q === "string" ? (
                    <li key={q}>
                      <code>{q}</code>
                    </li>
                  ) : (
                    <li key={q.id}>
                      <code>{q.id}</code> ({q.type}): {q.prompt}
                    </li>
                  ),
                )}
              </ul>
              {d.status === "pending" && <DraftActions id={d.id} action={decideDraft} />}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

function draftTitle(d: Draft): string {
  switch (d.kind) {
    case "questions":
      return `${d.payload.questions?.length ?? 0} Questions`;
    case "challenge":
      return `Daily Challenge for ${d.payload.day}`;
    case "stack":
      return `New Stack request: ${d.payload.name}`;
    case "syllabus": {
      const weeks = Array.isArray(d.payload.weeks) ? d.payload.weeks.length : 0;
      return `Weekly plan ${d.payload.version}, ${weeks} ${weeks === 1 ? "Week" : "Weeks"}`;
    }
  }
}
