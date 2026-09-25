# Content format

All Syllabus content lives in version folders, one per Stack version:

```
content/<stack-id>/<version>/syllabus.json              one Syllabus version
content/<stack-id>/<version>/questions/<lesson-id>.json one Question Bank per Lesson
content/<stack-id>/<version>/changelog.json             what changed since the version before
```

## Versions

A version is named for the day it was made: `v2026-09-26`. More versions on the same day add `.1`, `.2`, and so on: `v2026-09-26.1`.
- Versions sort by date, then by that number, so `v2026-09-26` < `v2026-09-26.1` < `v2026-09-26.2` < `v2026-09-26.10` < `v2026-09-27`.
- Compare versions with `version_key` in [`api/app/content/versions.py`](../api/app/content/versions.py), never as strings.
- The newest version is the Stack's current Syllabus.
- A version never changes once it is committed: the importer refuses changed content under a version it has already imported. A change is a new version.

`uv run --project api content-new-version <stack>` starts one. It copies the newest version to a folder with the next version name and changes only its `version`. It also starts a `changelog.json` naming the version it follows. `uv run --project api content-diff [<old>] <new>` lists what a version added, changed and removed (see [the changelog](#changelog-changelogjson)).

## Where it is defined

- **The format** is the Pydantic models in [`api/app/content/format.py`](../api/app/content/format.py). That file is the single definition of the format.
- **The JSON Schema files** [`content/schema/syllabus.schema.json`](../content/schema/syllabus.schema.json), [`question-bank.schema.json`](../content/schema/question-bank.schema.json) and [`changelog.schema.json`](../content/schema/changelog.schema.json) are generated from those models. Claude Code reads them when it writes content.
  - Regenerate them with `uv run content-schema` in `api/`.
  - A test and a CI step fail if they are out of date.
- **Rules that span several items** are in [`api/app/content/check.py`](../api/app/content/check.py), run with `uv run content-check ../content` in `api/`. They cover:
  - unique permanent IDs (see below);
  - the folder names match the Stack's `id` and the `version`;
  - references to Materials, Lessons and Concepts that must resolve;
  - at least two Questions per Concept, so a Retake always has a sibling;
  - 8–12 Questions per Question Bank, enough for a Lesson Quiz;
  - a changelog that matches what changed since the version before (see [the changelog](#changelog-changelogjson));
  - a permanent ID never comes back as a different kind of item in a later version;
  - Material links that load (with `--links`). A site that refuses automated requests (HTTP 401, 403 or 429) is only a warning.

Every problem is printed as `LEVEL file [item] message`. The item is the permanent ID of the thing at fault, such as the Question. For a format violation, the message starts with the path to the field. Any error fails the check; warnings don't.

The same check runs as the pre-commit hook and in CI. Material links are checked weekly, and on pull requests that change a Stack version (`.github/workflows/content-links.yml`).

## Permanent IDs

Every Stack, Week, Lesson, Milestone, Material, Concept and Question has an `id`:

- It is lowercase words joined by hyphens, at most 80 characters.
- It is unique across **every kind** within its Stack version. A Concept can't share an ID with a Lesson, and two Question Banks can't share a Concept or Question ID.
- It **never changes** across versions of that Stack. A revised item keeps its ID, and a new item gets an ID no version has used.
- It **is never reused**. An ID removed in one version never names a different item later. The check catches an ID that comes back as a different kind: an old Lesson ID used for a Concept, say.

Learner data (progress, answers, Milestone ticks) refers to content by `(stack id, permanent id)`, so it survives a new Syllabus version. That pair carries no kind, so one ID must mean one item.

A reused ID is reported in the file that reuses it, and the message names the kind and file that had the ID first. For example: `questions/w01-l02.json [concept-a] duplicate permanent id (Concept): already used by a Concept in questions/w01-l01.json`.

A Stack's `id` is also the name of its folder (`content/<stack-id>/<version>/`), so two Stacks can't claim the same ID.

## Syllabus (`syllabus.json`)

| Field | Contents |
|---|---|
| `schema_version` | Always `1` |
| `version` | This Syllabus version, such as `v2026-09-26` or `v2026-09-26.1` |
| `stack` | `{id, name, summary}` |
| `materials` | `{id, title, url, type, subject}`, where `type` is one of `book`, `docs`, `free`, `paid`, `paper`, `platform`, `tool`, `video`. The URL must be `https://`. |
| `weeks` | In order: `{id, number, title, goal, deliverable, interview_checks[], lessons[], milestones[]}` |

- A **Lesson** is `{id, title, topics[] (at least one), exercise (text or null), minutes, materials[]}`.
- A **Milestone** is `{id, title, kind (build or job-hunt), minutes, materials[]}`.
- In both, `materials` lists the IDs of Materials in the same file.

## Question Bank (`questions/<lesson-id>.json`)

| Field | Contents |
|---|---|
| `schema_version` | Always `1` |
| `lesson_id` | The Lesson's ID, which must match the file name |
| `concepts` | `{id, name}` for each Concept |
| `questions` | `{id, concept, type, prompt, explanation, materials[]}`, plus the fields for its type |

The extra fields depend on `type`:

- `multiple_choice`: `choices` (at least two `{id: "a".."h", text}`) and `answer` (the ID of one of the choices).
- `written`: `model_answer` (`{summary, key_points[]}` with at least two key points), and no choices.

The database stores the correct answers, but the API never sends them to the browser before the Learner has answered.

How to write a good Question Bank (sizes, mix, accuracy, IDs) is in [`.claude/skills/update-syllabus/question-bank-rules.md`](../.claude/skills/update-syllabus/question-bank-rules.md).

## Changelog (`changelog.json`)

Every version that follows another has a changelog: what changed since the version before, why, and the sources behind it. The Admin reads it when reviewing a Syllabus Update. A Stack's first version may have one too.

| Field | Contents |
|---|---|
| `schema_version` | Always `1` |
| `version` | This version, the same as `syllabus.json`'s |
| `previous_version` | The version before this one, or `null` for a Stack's first version |
| `summary` | What this version changes and why, in a few sentences |
| `changes` | One entry per change: `{kind, id, change, what, why, sources[]}` |

In each entry:
- `kind` is `stack`, `week`, `lesson`, `milestone`, `material`, `concept` or `question`;
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
  - it moves to another Week;
  - anything in its Question Bank changes, including gaining one (the field `question_bank`).
- A Lesson's position within its Week doesn't count.
- A Week is changed when its fields change, or its list of Lessons or Milestones does.
- The `version` string is never a change. So an untouched copy made by `content-new-version` has an empty diff.

The importer doesn't store the changelog, and it isn't part of a version's content hash.
