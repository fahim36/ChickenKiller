"use client";

import { type FormEvent, useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { Notice } from "@/components/Notice";
import type { QuestionReport } from "@/lib/api";
import { REPORT_STATUSES } from "@/lib/question-reports";
import { decideReport } from "./actions";

export function ReportDecision({ initial }: { initial: QuestionReport }) {
  const id = useId();
  const [report, setReport] = useState(initial);
  const [decision, setDecision] = useState<"accepted" | "closed">("accepted");
  const [explanation, setExplanation] = useState("");
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setFailed(false);
    try {
      setReport(await decideReport(report.id, decision, explanation));
    } catch {
      setFailed(true);
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className="space-y-3">
      <p>Status: {REPORT_STATUSES[report.status]}</p>
      {report.explanation && <p>Admin explanation: {report.explanation}</p>}
      {report.status === "open" && (
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label htmlFor={`${id}-decision`}>Decision</label>
            <select
              id={`${id}-decision`}
              value={decision}
              disabled={saving}
              onChange={(e) =>
                setDecision(e.target.value as "accepted" | "closed")
              }
              className="block rounded border bg-background p-2"
            >
              <option value="accepted">Accept, awaiting publication</option>
              <option value="closed">Close: declined or duplicate</option>
            </select>
          </div>
          <div>
            <label htmlFor={`${id}-explanation`}>
              Admin explanation (required)
            </label>
            <textarea
              id={`${id}-explanation`}
              required
              maxLength={4000}
              disabled={saving}
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              className="block w-full rounded border bg-background p-2"
            />
          </div>
          {failed && (
            <Notice tone="error" role="alert">
              Couldn&apos;t save the decision. Reload to check whether this
              report has already been decided.
            </Notice>
          )}
          <Button type="submit" disabled={saving || !explanation.trim()}>
            {saving ? "Saving…" : "Save decision"}
          </Button>
        </form>
      )}
    </div>
  );
}
