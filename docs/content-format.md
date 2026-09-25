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
- **Rules that span several items** are in [`api/app/content/check.py`](../api/app/content/check.py), run with `uv run content-check ../content`. They cover:
  - unique permanent IDs;
  - references to Materials, Lessons and Concepts that must resolve;
  - at least two Questions per Concept;
  - 8–12 Questions per Question Bank, enough for a Lesson Quiz;
  - Material links that load (with `--links`).

## Permanent IDs

Every Stack, Week, Lesson, Milestone, Material, Concept and Question has an `id`:

- It is lowercase words joined by hyphens, at most 80 characters.
- It is unique within its Stack version.
- It **never changes** across versions of that Stack.

Learner data (progress, answers, Milestone ticks) refers to content by `(stack id, permanent id)`, so it survives a new Syllabus version.

## Syllabus (`syllabus.json`)

| Field | Contents |
|---|---|
| `schema_version` | Always `1` |
| `version` | This Syllabus version, such as `v2026-09-26` |
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
