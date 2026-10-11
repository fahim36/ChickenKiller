"use client";

import Link from "next/link";
import { type FormEvent, useId, useState } from "react";
import { Notice } from "@/components/Notice";
import { Button } from "@/components/ui/button";
import type { QuestionReport, ReportCategory } from "@/lib/api";
import { saveReport } from "./actions";
import { REPORT_CATEGORIES, REPORT_STATUSES } from "@/lib/question-reports";

export function ReportForm({
  stackId,
  questionId,
  initial,
}: {
  stackId: string;
  questionId: string;
  initial: QuestionReport | null;
}) {
  const id = useId();
  const [category, setCategory] = useState<ReportCategory | "">(
    initial?.category ?? "",
  );
  const [note, setNote] = useState(initial?.note ?? "");
  const [report, setReport] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);
  const [saved, setSaved] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!category) return;
    setSaving(true);
    setFailed(false);
    setSaved(false);
    try {
      setReport(await saveReport(stackId, questionId, category, note));
      setSaved(true);
    } catch {
      setFailed(true);
    } finally {
      setSaving(false);
    }
  }
  return (
    <form onSubmit={submit} className="space-y-4">
      <p>
        Private to you and the Admin. Reporting changes no score or learning
        progress.
      </p>
      {report && <p>Status: {REPORT_STATUSES[report.status]}</p>}
      <div>
        <label htmlFor={`${id}-category`}>Category (required)</label>
        <select
          id={`${id}-category`}
          required
          disabled={saving}
          value={category}
          onChange={(e) => {
            setCategory(e.target.value as ReportCategory);
            setSaved(false);
          }}
          className="block rounded border p-2"
        >
          <option value="">Choose a category</option>
          {Object.entries(REPORT_CATEGORIES).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor={`${id}-note`}>Supporting note (optional)</label>
        <textarea
          id={`${id}-note`}
          disabled={saving}
          maxLength={4000}
          value={note}
          onChange={(e) => {
            setNote(e.target.value);
            setSaved(false);
          }}
          className="block w-full rounded border p-2"
        />
        <p className="text-sm">
          Up to 4,000 characters. Include only details needed to explain the
          defect.
        </p>
      </div>
      {failed && (
        <Notice tone="error" role="alert">
          Couldn&apos;t save this report. Reload to check its current status, or
          try again.
        </Notice>
      )}
      {saved && (
        <Notice tone="success" role="status">
          Report saved.{" "}
          <Link href="/question-reports">Your Question Reports</Link>
        </Notice>
      )}
      <Button type="submit" disabled={saving || !category}>
        {saving ? "Saving…" : report ? "Save changes" : "Submit report"}
      </Button>
    </form>
  );
}
