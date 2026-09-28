"""Write the Admin's accepted drafts into the repo, for the skills to merge.

    content-export-drafts [--content DIR]

Drafts come in through the MCP connector (app/mcp_server.py): new Questions, or a Daily
Challenge, each by one Learner. The Admin accepts or rejects them in the app. This writes each
accepted draft to `content/<stack-id>/drafts/<id>-<kind>.json`, with its author and note, and
marks it exported, so it is written once.

A draft file is not content: nothing reads `drafts/`. /update-syllabus merges a Questions draft
into the Question Bank and /write-challenges a Challenge draft into the Challenges, and
`content-check` checks the result as usual (Sources, siblings, the append-only baseline). Then
delete the draft file in the same commit. Prints each file written.

A new Stack (app/stack_builder.py) is different: nothing live to merge into, so its drafts are
content straight away. Its accepted weekly plan is written as the first version,
`content/<stack-id>/<version>/syllabus.json` (a first version has no changelog), and its
accepted Questions as `content/<stack-id>/question-bank/draft-<id>.json`, a Question Bank file.
The request itself writes nothing and is only marked exported. Then `content-check` and
`content-import` make the Stack live. A plan whose version folder exists already is left
accepted and reported.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import CONTENT_DIR
from app.content.loader import QUESTION_BANK_DIR
from app.db import SessionLocal
from app.models import ContentDraft, Learner, Stack


def export_drafts(session: Session, content_dir: Path, now: datetime) -> list[Path]:
    """Write every accepted draft and mark it exported. Commits."""
    rows = session.execute(
        select(ContentDraft, Learner.email)
        .join(Learner, Learner.id == ContentDraft.learner_id)
        .where(ContentDraft.status == "accepted")
        .order_by(ContentDraft.id)
    ).all()
    written = []
    for draft, email in rows:
        new_stack = session.get(Stack, draft.stack_id) is None
        if draft.kind == "stack":
            draft.status, draft.decided_at = "exported", now
            continue
        if new_stack and draft.kind in ("syllabus", "questions"):
            path = _new_stack_file(content_dir, draft)
            if path is None:
                continue
            written.append(path)
            draft.status, draft.decided_at = "exported", now
            continue
        folder = content_dir / draft.stack_id / "drafts"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{draft.id}-{draft.kind}.json"
        doc = {
            "draft": draft.id,
            "stack_id": draft.stack_id,
            "kind": draft.kind,
            "author": email,
            "note": draft.note,
            "submitted": draft.created_at.astimezone(UTC).isoformat(),
            **draft.payload,
        }
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        draft.status, draft.decided_at = "exported", now
        written.append(path)
    session.commit()
    return written


def _new_stack_file(content_dir: Path, draft: ContentDraft) -> Path | None:
    """Write a new Stack's weekly plan or Questions as content. None if the file exists."""
    stack_dir = content_dir / draft.stack_id
    if draft.kind == "syllabus":
        folder = stack_dir / str(draft.payload["version"])
        path = folder / "syllabus.json"
        doc = draft.payload
    else:
        folder = stack_dir / QUESTION_BANK_DIR
        path = folder / f"draft-{draft.id}.json"
        doc = {"schema_version": 2, **draft.payload}
    if path.exists():
        print(f"Skipped draft {draft.id}: {path} exists.", file=sys.stderr)
        return None
    folder.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write accepted drafts into content/.")
    parser.add_argument("--content", type=Path, default=CONTENT_DIR, help="the content root")
    args = parser.parse_args(argv)
    with SessionLocal() as session:
        written = export_drafts(session, args.content, datetime.now(UTC))
    for path in written:
        print(path)
    if not written:
        print("No accepted drafts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
