# Local time and placement UI polish

User-facing timestamps now format in the browser's local timezone, with consistent server/client initial markup. Date labels for scheduled Challenges use their local release date, and copied Result Cards use the same date as the display. UTC wording was removed from visible evidence and reporting copy; internal scoring and scheduling boundaries are unchanged.

Placement has a stronger Week entry, lesson cards, answer selection states, an answered-question progress bar, readable Lesson titles and a clearer result summary. Existing save, retry, ownership and final-submission behavior is preserved.

Verification: 267 frontend tests passed; 11 home-guidance backend checks passed. Typecheck, lint and backend formatting checks passed. Standards and Spec reviews found no blockers. The local desktop Week/result screens were inspected with the existing disposable Clerk learner. Mobile verification was interrupted by a browser timeout. Local production build was blocked/stalled by the worktree's external dependency junction; clean main CI is the final build gate. The desktop result screenshot is retained as a user-facing preview outside the repository.
