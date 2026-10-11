import Link from "next/link";
import { connection } from "next/server";
import { Notice } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { api, type ReportEligibility } from "@/lib/api";
import { ReportForm } from "../ReportForm";
import { REPORT_STATUSES } from "@/lib/question-reports";

export default async function NewReport({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  await connection();
  const { stack_id: stack, question_id: question } = await searchParams;
  const valid = typeof stack === "string" && !!stack && typeof question === "string" && !!question;
  const eligibility = valid ? await api<ReportEligibility>(`/stacks/${encodeURIComponent(stack)}/questions/${encodeURIComponent(question)}/report`) : null;
  return <main className="mx-auto max-w-3xl space-y-4">
    <PageHeader title="Question Report" crumbs={<Link href="/question-reports">Your Question Reports</Link>} />
    {!eligibility ? <Notice>Choose an answered Question from your practice to report.</Notice>
      : eligibility.retired_reason ? <Notice>This Question was retired: {eligibility.retired_reason}</Notice>
      : !eligibility.answered ? <Notice>Answer this Question before reporting it.</Notice>
      : eligibility.report && eligibility.report.status !== "open" ? <Notice>Status: {REPORT_STATUSES[eligibility.report.status]}. Only Open reports can be edited. {eligibility.report.explanation}</Notice>
      : valid && <ReportForm stackId={stack} questionId={question} initial={eligibility.report} />}
    <Link href="/">Back to Home</Link>
  </main>;
}
