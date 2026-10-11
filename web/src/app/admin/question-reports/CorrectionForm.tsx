"use client";

import { type FormEvent, useId, useState } from "react";
import { Notice } from "@/components/Notice";
import { Button } from "@/components/ui/button";
import { ReportCorrection } from "@/components/ReportCorrection";
import type { QuestionReport } from "@/lib/api";
import { associateCorrection } from "./actions";

export function CorrectionForm({ initial }: { initial: QuestionReport }) {
  const id = useId();
  const [report, setReport] = useState(initial);
  const [kind, setKind] = useState<"retirement" | "replacement">(
    initial.correction_kind ?? "retirement",
  );
  const [replacement, setReplacement] = useState(initial.replacement_id ?? "");
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);
  const [saved, setSaved] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setFailed(false);
    setSaved(false);
    try {
      setReport(
        await associateCorrection(
          report.id,
          kind,
          kind === "replacement" ? replacement.trim() : null,
        ),
      );
      setSaved(true);
    } catch {
      setFailed(true);
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className="space-y-3">
      <ReportCorrection report={report} />
      <form onSubmit={submit} className="space-y-3">
        <p>
          Associate the correction planned for {report.question_id}. This saves
          the plan; resolution waits for an import that matches it.
        </p>
        <label htmlFor={`${id}-kind`}>Correction outcome</label>
        <select
          id={`${id}-kind`}
          value={kind}
          disabled={saving}
          onChange={(e) => {
            setKind(e.target.value as "retirement" | "replacement");
            setSaved(false);
          }}
          className="block rounded border bg-background p-2"
        >
          <option value="retirement">Retirement without replacement</option>
          <option value="replacement">Retirement with replacement</option>
        </select>
        {kind === "replacement" && (
          <div>
            <label htmlFor={`${id}-replacement`}>
              Replacement Question ID (required)
            </label>
            <input
              id={`${id}-replacement`}
              required
              maxLength={80}
              disabled={saving}
              value={replacement}
              onChange={(e) => {
                setReplacement(e.target.value);
                setSaved(false);
              }}
              className="block rounded border bg-background p-2"
            />
            <p>
              The permanent ID in the planned content correction. It may be
              imported later.
            </p>
          </div>
        )}
        {failed && (
          <Notice tone="error" role="alert">
            Couldn&apos;t associate this correction. Reload to check the
            report&apos;s current status.
          </Notice>
        )}
        {saved && (
          <Notice role="status">
            Correction association saved. Awaiting matching import.
          </Notice>
        )}
        <Button
          type="submit"
          disabled={saving || (kind === "replacement" && !replacement.trim())}
        >
          {saving ? "Saving…" : "Save correction association"}
        </Button>
      </form>
    </div>
  );
}
