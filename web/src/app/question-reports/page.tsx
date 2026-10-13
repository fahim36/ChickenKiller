import { LocalTime } from "@/components/LocalTime";
import Link from "next/link";
import { connection } from "next/server";
import { PageHeader } from "@/components/PageHeader";
import { Notice } from "@/components/Notice";
import { ReportCorrection } from "@/components/ReportCorrection";
import { api, type QuestionReport } from "@/lib/api";
import { REPORT_CATEGORIES, REPORT_STATUSES } from "@/lib/question-reports";

export default async function YourReports() {
  await connection();
  const reports = await api<QuestionReport[]>("/me/question-reports");
  return (
    <main className="mx-auto max-w-3xl space-y-4">
      <PageHeader
        title="Your Question Reports"
        crumbs={<Link href="/">Home</Link>}
        description="Private to you and the Admin. Scores and learning progress are unchanged."
      />
      {!reports ? (
        <Notice>Your reports couldn&apos;t be loaded. Try again.</Notice>
      ) : !reports.length ? (
        <p>
          No Question Reports yet. Report a Question after answering it in
          practice.
        </p>
      ) : (
        <ul className="space-y-4">
          {reports.map((r) => (
            <li key={r.id} className="rounded border p-4 space-y-2">
              <h2 className="font-semibold">
                {REPORT_CATEGORIES[r.category]} · {r.stack_id} / {r.question_id}
              </h2>
              <p>Status: {REPORT_STATUSES[r.status]}</p>
              <p>
                Updated <LocalTime value={r.updated_at} />
              </p>
              {r.note && <p className="whitespace-pre-wrap">{r.note}</p>}
              {r.explanation && <p>Admin explanation: {r.explanation}</p>}
              <ReportCorrection report={r} />
              {r.status === "open" && (
                <Link
                  className="underline"
                  href={`/question-reports/new?stack_id=${encodeURIComponent(r.stack_id)}&question_id=${encodeURIComponent(r.question_id)}`}
                >
                  Edit Open report
                </Link>
              )}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
