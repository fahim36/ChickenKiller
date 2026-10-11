import type { ReportCategory } from "./api";

export const REPORT_CATEGORIES: Record<ReportCategory, string> = {
  wrong_answer: "Wrong answer",
  ambiguous_wording: "Ambiguous wording",
  outdated_claim: "Outdated claim",
  broken_source: "Broken Source",
};
export const REPORT_STATUSES = {
  open: "Open",
  accepted: "Accepted, awaiting publication",
  resolved: "Resolved",
  closed: "Closed",
};
