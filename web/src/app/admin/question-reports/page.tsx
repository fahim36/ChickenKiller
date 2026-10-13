import { LocalTime } from "@/components/LocalTime";
import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Inline } from "@/components/Inline";
import { Notice } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { api, type Me, type QuestionReportGroup } from "@/lib/api";
import { REPORT_CATEGORIES } from "@/lib/question-reports";
import { ReportDecision } from "./ReportDecision";

export default async function ReportQueue() {
  await connection();
  const me = await api<Me>("/me");
  if (!me?.is_admin) notFound();
  const groups = await api<QuestionReportGroup[]>("/admin/question-reports");
  return (
    <main className="mx-auto max-w-4xl space-y-4">
      <PageHeader
        title="Question Reports"
        crumbs={<Link href="/settings">Settings</Link>}
        description="Private reports grouped by Question. Acceptance awaits a correction through the reviewed content process; it publishes nothing and changes no scores."
      />
      {!groups ? (
        <Notice>Reports couldn&apos;t be loaded. Try again.</Notice>
      ) : !groups.length ? (
        <p>No Question Reports yet.</p>
      ) : (
        <ul aria-label="Reported Questions" className="space-y-5">
          {groups.map((group) => (
            <li
              key={`${group.stack_id}/${group.question_id}`}
              className="rounded-2xl border bg-card p-5 space-y-4"
            >
              <h2 className="font-semibold">
                {group.stack_id} / {group.question_id}
              </h2>
              <p>
                <Inline text={group.prompt} />
              </p>
              {group.retired_reason && (
                <Notice>Retired: {group.retired_reason}</Notice>
              )}
              <p>
                {group.reports.length} report
                {group.reports.length === 1 ? "" : "s"}
              </p>
              <ul
                aria-label={`Reports for ${group.question_id}`}
                className="space-y-4"
              >
                {group.reports.map((report) => (
                  <li key={report.id} className="rounded border p-4 space-y-3">
                    <p>
                      {REPORT_CATEGORIES[report.category]} ·{" "}
                      {report.reporter_email}
                    </p>
                    <p>
                      Reported <LocalTime value={report.created_at} />
                    </p>
                    {report.note && (
                      <p className="whitespace-pre-wrap">{report.note}</p>
                    )}
                    <ReportDecision initial={report} />
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
