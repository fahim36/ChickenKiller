# Content format

All Syllabus content lives in version folders, one per Stack version:

```
content/<stack-id>/<version>/syllabus.json              one Syllabus version
content/<stack-id>/<version>/questions/<lesson-id>.json one Question Bank per Lesson
```

Each version is a date, such as `v2026-09-26`, and newer versions sort after older ones.

## Where it is defined

- **The format** is the Pydantic models in [`api/app/content/format.py`](../api/app/content/format.py). That file is the single definition of the format.
- **The JSON Schema files** [`content/schema/syllabus.schema.json`](../content/schema/syllabus.schema.json) and [`question-bank.schema.json`](../content/schema/question-bank.schema.json) are generated from those models. Claude Code reads them when it writes content.
  - Regenerate them with `uv run content-schema` in `api/`.
  - A test and a CI step fail if they are out of date.
- **Rules that span several items** are in [`api/app/content/check.py`](../api/app/content/check.py), run with `uv run content-check ../content` in `api/`. They cover:
  - unique permanent IDs (see below);
  - the folder names match the Stack's `id` and the `version`;
  - references to Materials, Lessons and Concepts that must resolve;
  - at least two Questions per Concept, so a Retake always has a sibling;
  - 8–12 Questions per Question Bank, enough for a Lesson Quiz;
  - Material links that load (with `--links`). A site that refuses automated requests (HTTP 401, 403 or 429) is only a warning.

Every problem is printed as `LEVEL file [item] message`. The item is the permanent ID of the thing at fault, such as the Question. For a format violation, the message starts with the path to the field. Any error fails the check; warnings don't.

The same check runs as the pre-commit hook and in CI. Material links are checked weekly, and on pull requests that change a Stack version (`.github/workflows/content-links.yml`).

## Permanent IDs

Every Stack, Week, Lesson, Milestone, Material, Concept and Question has an `id`:

- It is lowercase words joined by hyphens, at most 80 characters.
- It is unique across **every kind** within its Stack version. A Concept can't share an ID with a Lesson, and two Question Banks can't share a Concept or Question ID.
- It **never changes** across versions of that Stack.

Learner data (progress, answers, Milestone ticks) refers to content by `(stack id, permanent id)`, so it survives a new Syllabus version. That pair carries no kind, so one ID must mean one item.

A reused ID is reported in the file that reuses it, and the message names the kind and file that had the ID first. For example: `questions/w01-l02.json [concept-a] duplicate permanent id (Concept): already used by a Concept in questions/w01-l01.json`.

A Stack's `id` is also the name of its folder (`content/<stack-id>/<version>/`), so two Stacks can't claim the same ID.

## Syllabus (`syllabus.json`)

| Field | Contents |
|---|---|
| `schema_version` | Always `1` |
| `version` | This Syllabus version, such as `v2026-09-26` |
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
- A later version can publish it, or withdraw it by setting `false`. Learners whose Active Stack is withdrawn keep it and their progress; nobody new can pick it.

Leaving `published` out and writing `"published": true` are the same content, so versions written before the field existed still import unchanged.

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
