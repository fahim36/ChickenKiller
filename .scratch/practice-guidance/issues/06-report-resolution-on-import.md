# 06: Resolve accepted Question Reports when their correction is imported

**What to build:** A reporter sees Resolved only after the correction associated with their accepted Question Report has reached the imported app content.

**Blocked by:** 05: Let Admins review Question Reports grouped by Question.

**Status:** draft (proposed ready-for-agent; not published to GitHub)

- [ ] Associate an accepted report with its expected retirement/replacement outcome using permanent Question IDs, and make the association reviewable by the Admin.
- [ ] After import confirms that exact outcome, mark the associated accepted report Resolved and expose the resolution in reporter/Admin views.
- [ ] An unrelated import, an unimported content draft, failed import or Admin acceptance alone cannot resolve a report.
- [ ] Repeated imports/transitions are idempotent; correction verification and resolution cannot claim success before the relevant import commits.
- [ ] Keep the existing reviewed content pipeline and immutable-Question rules; preserve recorded scores and report privacy.
- [ ] Import/API/UI checks cover correct and unrelated imports, missing replacement, transaction failure, retries and in-app status updates.

