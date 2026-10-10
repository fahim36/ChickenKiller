# 05: Let Admins review Question Reports grouped by Question

**What to build:** An Admin can inspect corroborating reports, accept a defect awaiting publication or close a report with an explanation, and the reporter sees the decision.

**Blocked by:** 04: Let Learners submit and track private Question Reports.

**Status:** draft (proposed ready-for-agent; not published to GitHub)

- [ ] Group private reports by Question in an Admin-only queue while keeping other reporters hidden from each Learner.
- [ ] Allow Open reports to become Accepted, awaiting publication, or Closed for declined/duplicate reports; require an Admin explanation.
- [ ] Reporter status views display the decision and explanation, and accepted reports can no longer be edited.
- [ ] Accepting a report neither publishes content nor marks it Resolved; route corrections through the existing reviewed immutable-content pipeline.
- [ ] Transitions are validated and repeated/concurrent decisions cannot silently overwrite an already decided report.
- [ ] API/UI checks demonstrate grouped review, explanation validation, privacy, transition protection and unchanged learning results.

