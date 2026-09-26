# All days are UTC days

Every Day boundary in the app is 00:00 UTC: Daily Challenges release then, and Streaks count UTC Days. We chose one global clock over each Learner's local time zone because a Daily Challenge is a shared event, so "#40" should mean the same Challenge on the same Day for everyone, and one boundary is simpler to build and test than per-Learner ones.

## Consequences

- Onboarding no longer asks for a time zone.
- A Learner's Day can reset at an awkward local hour: 06:00 in Dhaka, but mid-afternoon or evening in the Americas.
- The app labels Challenges by number and UTC date ("#40 · 26 Sep") so the boundary is visible.
