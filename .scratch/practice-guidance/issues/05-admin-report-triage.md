# 05: Let Admins review Question Reports grouped by Question

**What to build:** An Admin can inspect corroborating reports, accept a defect awaiting publication or close a report with an explanation, and the reporter sees the decision.

**Blocked by:** 04: Let Learners submit and track private Question Reports.

**Status:** complete (verified locally; branch push tracked in docs/practice-guidance-progress.md)

- [x] Group private reports by Question in an Admin-only queue while keeping other reporters hidden from each Learner.
- [x] Allow Open reports to become Accepted, awaiting publication, or Closed for declined/duplicate reports; require an Admin explanation.
- [x] Reporter status views display the decision and explanation, and accepted reports can no longer be edited.
- [x] Accepting a report neither publishes content nor marks it Resolved; route corrections through the existing reviewed immutable-content pipeline.
- [x] Transitions are validated and repeated/concurrent decisions cannot silently overwrite an already decided report.
- [x] API/UI checks demonstrate grouped review, explanation validation, privacy, transition protection and unchanged learning results.

