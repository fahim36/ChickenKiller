import type { QuestionReport } from "@/lib/api";

export function ReportCorrection({ report }: { report: QuestionReport }) {
  if (!report.correction_kind) return null;
  return (
    <div className="space-y-1">
      <p>
        Expected correction:{" "}
        {report.correction_kind === "replacement"
          ? `retire this Question and replace it with ${report.replacement_id}`
          : "retire this Question without a replacement"}
        .
      </p>
      {report.resolved_at && (
        <p>Correction imported {report.resolved_at.slice(0, 10)} UTC.</p>
      )}
      {report.resolution_reason && (
        <p>Retirement reason: {report.resolution_reason}</p>
      )}
    </div>
  );
}
