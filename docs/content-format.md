# Content format

Each Stack has a folder holding its Syllabus versions and its one Question Bank:

```
content/<stack-id>/<version>/syllabus.json       one Syllabus version
content/<stack-id>/<version>/changelog.json      what changed since the version before
content/<stack-id>/question-bank/<name>.json     the Stack's Question Bank, never versioned
content/<stack-id>/challenges/launch.json        the Day of the Stack's Daily Challenge #1
content/<stack-id>/challenges/<number>.json      one Daily Challenge, such as 001.json
```

The Syllabus is versioned and each new version replaces the old one. The Question Bank is not: it only grows, and a Question is never edited or deleted once committed ([ADR-0004](adr/0004-append-only-question-bank-with-sources.md)). See [the Question Bank](#question-bank-question-bankjson). The Daily Challenges aren't versioned either, and each is frozen from 00:00 UTC on its Day. See [Daily Challenges](#daily-challenges-challenges).

Until #15 each version folder held its own banks, in `<version>/questions/<lesson-id>.json`. Nothing had been released, so the two committed versions of `agentic-ai-engineer` are rewritten into this layout **once**, by `content-migrate-bank` (see [Moving to the Stack's Question Bank](#moving-to-the-stacks-question-bank)). A version folder that still has a `questions/` folder fails the check.

## Versions

A version is named for the day it was made: `v2026-09-26`. More versions on the same day add `.1`, `.2`, and so on: `v2026-09-26.1`.
- Versions sort by date, then by that number, so `v2026-09-26` < `v2026-09-26.1` < `v2026-09-26.2` < `v2026-09-26.10` < `v2026-09-27`.
- Compare versions with `version_key` in [`api/app/content/versions.py`](../api/app/content/versions.py), never as strings.
- The newest version is the Stack's current Syllabus.
- A version never changes once it is committed: the importer refuses changed content under a version it has already imported. A change is a new version.

`uv run --project api content-new-version <stack>` starts one. It copies the newest version's `syllabus.json` to a folder with the next version name and changes only its `version`; the Question Bank stays where it is. It also starts a `changelog.json` naming the version it follows. `uv run --project api content-diff [<old>] <new>` lists what a version added, changed and removed (see [the changelog](#changelog-changelogjson)), then what the Question Bank added, retired and re-tagged since git `HEAD` (`--baseline <ref>` for another ref).

## Where it is defined

- **The format** is the Pydantic models in [`api/app/content/format.py`](../api/app/content/format.py). That file is the single definition of the format.
- **The JSON Schema files** [`content/schema/syllabus.schema.json`](../content/schema/syllabus.schema.json), [`question-bank.schema.json`](../content/schema/question-bank.schema.json), [`changelog.schema.json`](../content/schema/changelog.schema.json), [`challenge.schema.json`](../content/schema/challenge.schema.json) and [`challenge-launch.schema.json`](../content/schema/challenge-launch.schema.json) are generated from those models. Claude Code reads them when it writes content.
  - Regenerate them with `uv run content-schema` in `api/`.
  - A test and a CI step fail if they are out of date.
- **Rules that span several items** are in [`api/app/content/check.py`](../api/app/content/check.py), run with `uv run content-check ../content` in `api/`. It checks each Stack whole: every version, and the Question Bank. The rules cover:
  - unique permanent IDs (see below);
  - the folder names match the Stack's `id` and the `version`;
  - references to Materials, Lessons and Concepts that must resolve;
  - at least two Questions per Concept that aren't retired, so a Retake always has a sibling;
  - at least 8 Questions per Lesson that aren't retired, with 4 multiple choice and 2 multiple select (a legacy written Question counts as one), enough for a Lesson Quiz (no maximum: the bank only grows);
  - a multiple-select Question's `answers` are some of its choices, not all;
  - Sources, retirements and the append-only rules (see [the Question Bank](#question-bank-question-bankjson));
  - Daily Challenges: numbered and dated from the launch, three Questions each (two multiple choice, then one multiple select), frozen once released (see [Daily Challenges](#daily-challenges-challenges));
  - a changelog that matches what changed since the version before (see [the changelog](#changelog-changelogjson));
  - a permanent ID never comes back as a different kind of item in a later version;
  - Material links that load (with `--links`). A site that refuses automated requests (HTTP 401, 403 or 429) is only a warning.

Every problem is printed as `LEVEL file [item] message`. The item is the permanent ID of the thing at fault, such as the Question. For a format violation, the message starts with the path to the field. Any error fails the check; warnings don't.

`content-check` takes `--baseline <git ref>` (default `HEAD`) and `--today <YYYY-MM-DD>` (default: today in UTC) for the append-only and frozen-Challenge rules. For each Stack with Daily Challenges it also prints how far ahead they are written: `content/agentic-ai-engineer: Challenges written through 2026-10-03 (7 Days left)`.

The same check runs as the pre-commit hook (against `HEAD`) and in CI (against a pull request's base, with "today" the UTC day of its last commit). Material links are checked weekly, and on pull requests that change a Stack version (`.github/workflows/content-links.yml`).

## Permanent IDs

Every Stack, Week, Lesson, Milestone, Material, Concept and Question has an `id`:

- It is lowercase words joined by hyphens, at most 80 characters.
- It is unique across **every kind** within its Stack version and the Question Bank. A Concept can't share an ID with a Lesson of the newest version, and two Question Bank files can't share a Concept or Question ID.
- It **never changes** across versions of that Stack. A revised item keeps its ID, and a new item gets an ID no version has used.
- It **is never reused**. An ID removed in one version never names a different item later. The check catches an ID that comes back as a different kind: an old Lesson ID used for a Concept, say.

Learner data (progress, answers, Milestone ticks) refers to content by `(stack id, permanent id)`, so it survives a new Syllabus version. That pair carries no kind, so one ID must mean one item.

A reused ID is reported in the file that reuses it, and the message names the kind and file that had the ID first. For example: `question-bank/w01-l02.json [concept-a] duplicate permanent id (Concept): already used by a Concept in question-bank/w01-l01.json`.

A Stack's `id` is also the name of its folder (`content/<stack-id>/<version>/`), so two Stacks can't claim the same ID.

## Syllabus (`syllabus.json`)

| Field | Contents |
|---|---|
| `schema_version` | Always `1` |
| `version` | This Syllabus version, such as `v2026-09-26` or `v2026-09-26.1` |
| `stack` | `{id, name, summary, published}`. `published` is optional and defaults to `true`; see below. |
| `materials` | `{id, title, url, type, subject}`, where `type` is one of `book`, `docs`, `free`, `paid`, `paper`, `platform`, `tool`, `video`. The URL must be `https://`. |
| `weeks` | In order: `{id, number, title, goal, deliverable, interview_checks[], lessons[], milestones[]}` |

- A **Lesson** is `{id, title, topics[] (at least one), exercise (text or null), minutes, materials[]}`.
- A **Milestone** is `{id, title, kind (build or job-hunt), minutes, materials[]}`.
- In both, `materials` lists the IDs of Materials in the same file.

### Published Stacks

Learners can only pick a published Stack, during onboarding or in settings. A Stack's current Syllabus decides whether it is published:

- Leave `published` out (or set it to `true`) to publish the Stack when that version is imported.
- Set `"published": false` to import a Stack before it is ready, for example while working through a Stack Request. It is left off the list of Stacks.
- A later version can publish it, or withdraw it by setting `false`. Learners who have it as an Active Stack keep it and their progress; nobody new can activate it, and a Learner who deactivates it cannot activate it again.

Leaving `published` out and writing `"published": true` are the same content, so versions written before the field existed still import unchanged.

## Question Bank (`question-bank/*.json`)

A Stack has one Question Bank: every file in `content/<stack-id>/question-bank/`. Files only group Questions for readable diffs (one per Lesson is usual, `<lesson-id>.json`); a Question's Lesson is a field on it, so re-tagging it doesn't move it, and a Concept declared in one file can be tested in another. Concepts belong to the Stack too.

Each file:

| Field | Contents |
|---|---|
| `schema_version` | Always `2` |
| `concepts` | `{id, name}` for each Concept |
| `questions` | `{id, lesson, concept, type, prompt, explanation, materials[], sources[], retired}`, plus the fields for its type |

The extra fields depend on `type`:

- `multiple_choice`: `choices` (at least two `{id: "a".."h", text}`) and `answer` (the ID of one of the choices).
- `multiple_select` ("select all that apply"): `choices` (4 to 6 `{id: "a".."h", text}`, unique IDs) and `answers` (the IDs of **every** correct choice, each listed once: at least two, and at least one choice is wrong). Its prompt ends "Select all that apply." A Learner's answer is correct only when the choices ticked are exactly `answers`: all or nothing, never graded.
- `written` (**legacy**, [ADR-0008](adr/0008-multiple-select-replaces-written-questions.md)): `model_answer` (`{summary, key_points[]}` with at least two key points), and no choices. The committed ones stay (released Daily Challenges use some), but a new Question is never written: the check refuses one. Each is retired, `replaced_by` a multiple-select Question on the same Concept.

For example:

```json
{
  "id": "w01-l01-q13",
  "lesson": "w01-l01",
  "concept": "w01-l01-tool-loop",
  "type": "multiple_select",
  "prompt": "Which of these does an agent loop do on every turn? Select all that apply.",
  "choices": [
    {"id": "a", "text": "Send the conversation so far to the model"},
    {"id": "b", "text": "Retrain the model on the last tool result"},
    {"id": "c", "text": "Run any tool calls the model asked for"},
    {"id": "d", "text": "Clear the earlier turns from the context window"}
  ],
  "answers": ["a", "c"],
  "explanation": "...",
  "materials": [],
  "sources": [{"url": "https://...", "title": "...", "publisher": "...", "accessed": "2026-10-03", "claim": "..."}],
  "retired": null
}
```

In each Question:

- `lesson` is the ID of the Lesson it is tagged to, or `null` (or left out) for none. A Question that isn't retired must be tagged to a Lesson of the Stack's **newest** Syllabus version.
- `materials` lists Material IDs, which resolve against the Stack's **newest** Syllabus version. A Syllabus Update can't drop a Material that a Question in use still names (retire the Question instead).
- `sources` has at least one `{url, title, publisher, accessed, claim}`: the `https://` page the Question's content came from, its title and publisher, the UTC date it was read (`YYYY-MM-DD`), and the claim the Question relies on. A Source is for checking a Question; a Material is for learning.
- `retired`, once set, makes it a Retired Question: `{reason, replaced_by, on}`, where `reason` is required, `replaced_by` is the ID of the Question that replaces it (it must be in the bank), and `on` is the UTC date. A Retired Question stays in the bank but is never drawn for anything new: not a Lesson Quiz, a Retake or Review. It doesn't count toward any minimum, and its Lesson tag and Materials may name things that are gone.

The database stores the correct answers, but the API never sends them to the browser before the Learner has answered.

### Append-only

"Committed" means the git baseline: `HEAD` for the pre-commit hook, the pull request's base in CI (`--baseline`). Against it (`api/app/content/baseline.py`):

- **A committed Question is never deleted.** Retire it instead.
- **A committed Question never changes**, except by adding `retired` or changing its `lesson`. Anything else (its prompt, answer, Concept, Materials, Sources) is an error naming the fields. A retirement is final: it is never edited or undone.
- **A new Question's Sources are from this run**: every `accessed` date is today or yesterday in UTC (by `--today`), so a run that crosses 00:00 UTC still passes. Committed Questions keep their dates.
- **A new Question on a Concept that committed Questions already test is a warning**, naming one of them. A repeat is allowed; the warning makes it deliberate.
- **A new Question is never written** ([ADR-0008](adr/0008-multiple-select-replaces-written-questions.md)): `a new Question is never written: written Questions are legacy (ADR-0008); write it as multiple_select`.
- **A new multiple-choice Question whose correct choice is clearly the longest is a warning**: more than 25% and at least 8 characters longer than every wrong choice, since length gives the answer away. **So is a new multiple-select Question whose correct choices are each longer than every wrong choice** ("the correct choices (a, c) are clearly the longest"). Committed Questions can't be edited, so they aren't warned about.

Outside a git repository (a test folder, say) there is no baseline: these rules are skipped, with a warning that says so. A Stack new since the baseline has an empty one, so all its Questions are new. A baseline in the old layout (before #15) is read from its version folders, newest version winning, with each Question tagged to its file's Lesson; those Questions may gain Sources once, and an edit to one is a warning rather than an error, since nothing had been released before the move.

The importer loads the bank on every import, with each Question's Sources and retirement. It adds new Concepts and Questions, applies retirements and re-tags, and refuses an edited or un-retired Question. It never deletes one, so re-running an import changes nothing.

How to write good Questions (sizes, mix, accuracy, IDs) is in [`.claude/skills/update-syllabus/question-bank-rules.md`](../.claude/skills/update-syllabus/question-bank-rules.md).

### Moving to the Stack's Question Bank

```
uv run --project api content-migrate-bank content/<stack-id> --sources <dir> [--dry-run]
```

A one-time rewrite of a Stack from the old layout ([`api/app/content/migrate_bank.py`](../api/app/content/migrate_bank.py)):

- every version's `questions/<lesson-id>.json` is merged into `question-bank/<lesson-id>.json`, the newest version winning for an ID in several, each Question tagged to its file's Lesson;
- each Question's Sources come from sidecar files in `--sources`, one per Lesson: `{"lesson_id": ..., "questions": {<id>: {"sources": [...], "problem": null}}}`. A `problem` (a factual error found) retires the Question with that reason;
- changelog entries that only described a Question Bank are dropped: the changelog now covers the Syllabus only;
- every version's `questions/` folder is removed.

It prints a report: Questions without Sources, Questions retired, changelog entries dropped. Run the check afterwards: a retirement can leave a Concept or Lesson short, which needs new Questions.

When `agentic-ai-engineer` was migrated, writing its Sources turned up factual slips in five Questions and one Material title. Nothing had been released, so they were fixed in place in the old layout (in `v2026-09-26.1`, IDs kept) just before the rewrite, not retired, and the check against the old-layout baseline reports each as a warning: `w01-l05-q03` (the keyed answer had the error case backwards), `w02-l04-q12` (RFC 9110's wording for 5xx), `w10-l05-q08` (partitioned indices restrict access per organization, not per user), `w12-l03-q05` (regional endpoints cost 10% more than global), `w12-l05-q03` (the Dockerfile reference's signal warning is under ENTRYPOINT) and the Laszlo Bock Material's title. From then on the bank is append-only: a mistake means retiring the Question and adding a new one.

## Daily Challenges (`challenges/`)

A Stack's Daily Challenges are the files of `content/<stack-id>/challenges/`, written ahead by `/write-challenges <stack> <days>` ([.claude/skills/write-challenges/SKILL.md](../.claude/skills/write-challenges/SKILL.md)). Like the Question Bank they belong to the Stack, not to a Syllabus version.

`launch.json` holds the Stack's launch Day, the UTC Day of Challenge #1:

| Field | Contents |
|---|---|
| `schema_version` | Always `1` |
| `launch` | `YYYY-MM-DD` |

Each Challenge is `<number>.json`, zero-padded to three digits (`001.json`, ..., `999.json`, then `1000.json`):

| Field | Contents |
|---|---|
| `schema_version` | Always `1` |
| `number` | From 1, counting from the launch |
| `date` | Its UTC Day, `YYYY-MM-DD`: the launch Day plus `number` − 1 Days |
| `questions` | Three Question IDs of the Stack's Question Bank: two multiple choice, then one multiple select |

The check holds them to these rules (`--today` is the clock):

- A file's name is its `number`, and its `date` follows from the launch Day. So numbers and dates are consecutive from the launch, and a Challenge can't move to another Day.
- **A Day with no Challenge written has no Challenge.** Gaps are allowed: a Stack that runs out has no Challenge on those Days, and numbering carries on from the launch.
- Every Question is in the bank, and the Questions are two multiple choice, then one multiple select, in that order ([ADR-0008](adr/0008-multiple-select-replaces-written-questions.md)): `a Daily Challenge is 2 multiple-choice Questions, then 1 multiple-select; this one is ...`. Before ADR-0008 a Challenge was two multiple choice and one written, so:
  - a released Challenge (its Day is today or earlier) keeps that mix for good;
  - an Upcoming Challenge committed with it and unchanged since (byte for byte, against the baseline; any, outside git) is only a warning, `an Upcoming Challenge with a written Question, committed before written Questions became legacy (ADR-0008): rewrite it as 2 multiple-choice Questions, then 1 multiple-select, before its Day`. Changing it, or retiring its written Question, means rewriting it in the new mix.
- A Question can be one written for the Challenge (`question-bank/challenge-<number>.json`, tagged to a Lesson or not) or an older one.
- An Upcoming Challenge (its Day is after today) uses no Retired Question, since one can't be answered. A released Challenge keeps a Question retired after its Day: the Archive shows it retired ([ADR-0004](adr/0004-append-only-question-bank-with-sources.md)).
- Its new Questions follow the bank's rules like any other: Sources accessed in this run, a sibling for every Concept.
- Fewer than three Days left is a warning: `Challenges written through 2026-10-03 (2 Days left): write more with /write-challenges; ...`. Days left count from today to the last Challenge's Day, both included, so a gap before it doesn't count against it; a launched Stack with none written has 0.

**Frozen.** Against the git baseline (`api/app/content/baseline.py`), a Challenge is released at 00:00 UTC on its Day, so one whose Day is today (UTC) or earlier is frozen:

- it never changes, byte for byte (line endings aside), and is never deleted;
- a Day that has begun (today or earlier) never gets a Challenge it didn't have when committed.

Only Challenges for future Days are Upcoming Challenges: they can be edited or deleted until 23:59:59 UTC the Day before. The check's clock is a date (`--today`, the UTC day of the commit in CI), so a Challenge committed on the Day before its own passes. Moving `launch` would re-date every Challenge, so once one is released the frozen rule refuses it too. Outside git the frozen rules are skipped, with the same warning as the bank's.

The importer loads the Challenges on every import, by the UTC Day of the import. A new Challenge is added (even one whose Day has begun, which was checked when it was committed); an Upcoming one is updated, or removed when its file is gone; a released one that differs from what is stored, or is gone, is refused, changing nothing. Re-running an import changes nothing. The API never sends an Upcoming Challenge's Questions to a Learner: the Admin's **Upcoming Challenges** page (`/admin/challenges`) only shows each Stack's "Challenges written through <date> (<n> Days left)", with the same warning.

How to write a Challenge's Questions is in [`.claude/skills/write-challenges/challenge-rules.md`](../.claude/skills/write-challenges/challenge-rules.md), on top of the bank's rules.

## Changelog (`changelog.json`)

Every version that follows another has a changelog: what changed in the Syllabus since the version before, why, and the sources behind it. The Admin reads it when reviewing a Syllabus Update. A Stack's first version may have one too.

Questions get no entries. Each new Question carries its own Sources, and each retirement its reason and replacement; a re-tag usually follows a Lesson change the changelog lists. What a Syllabus Update did to the bank is listed by `content-diff`, against git, for review, and the `summary` gives its counts. The bank's changes can't be held to a version once committed (the check compares the bank with git, not with a version), so listing them in a version's changelog would be a second record nothing keeps true. A version that changes only the bank has an empty `changes`.

| Field | Contents |
|---|---|
| `schema_version` | Always `1` |
| `version` | This version, the same as `syllabus.json`'s |
| `previous_version` | The version before this one, or `null` for a Stack's first version |
| `summary` | What this version changes and why, in a few sentences, with the Question Bank's counts (added, retired, re-tagged) |
| `changes` | One entry per change: `{kind, id, change, what, why, sources[]}` |

In each entry:
- `kind` is `stack`, `week`, `lesson`, `milestone` or `material` (an entry for a `concept` or `question` is refused, since the Question Bank isn't part of a version);
- `change` is `added`, `changed` or `removed`;
- `what` says what changed, and `why` says why;
- `sources` lists at least one `https://` URL, from primary sources.

**The check holds the changelog to the diff.** `content-diff` compares the two versions by permanent ID. Then:
- **every Lesson** that was added, changed or removed has an entry with the same `change`;
- **every entry** matches the diff, whatever its kind. An entry for something that didn't change, or that changed another way, is an error;
- no item is listed twice;
- `version` and `previous_version` name this folder and the version before it.

What counts as a change:
- A Lesson is **changed** when:
  - its own fields change: `title`, `topics`, `exercise`, `minutes` or `materials`;
  - it moves to another Week.
- A Lesson's position within its Week doesn't count.
- A Week is changed when its fields change, or its list of Lessons or Milestones does.
- The `version` string is never a change. So an untouched copy made by `content-new-version` has an empty diff.

The importer doesn't store the changelog, and it isn't part of a version's content hash.

The importer also stores, with each version's Lessons, the Questions tagged to them (not retired) when the version was imported, and a fingerprint of the Lesson's fields, Week and those Questions. A Learner's Completed Lesson is an Updated Lesson when that fingerprint differs from the version they completed it in, and its new Questions are the ones the Question Bank tags to it now that that version didn't, less any the Learner has already answered (#13). So a Syllabus Update that adds or re-tags Questions to a Lesson updates it even though the changelog doesn't list it. Questions added without a new version (with a Daily Challenge, say) join the Lesson's pool and never make a Lesson Updated; for a Learner whose Lesson is already Updated, they are new Questions too.

A Syllabus Update that removes a Lesson retires its Questions, re-tags them to another Lesson, or tags them to none (`"lesson": null`), since a Question in use must be tagged to a current Lesson or none. Untagged, they stay in the bank for Daily Challenges and Review: no Lesson Quiz draws them, but a Learner's Missed Question among them stays in their Review.
