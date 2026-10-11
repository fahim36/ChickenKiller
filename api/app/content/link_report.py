"""Offline content selection and explicit, separately scheduled link availability probes."""

import argparse
import json
import subprocess
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.content.check import stack_folders, version_folders
from app.content.loader import ContentError, read_bank, read_folder


@dataclass(frozen=True)
class Reference:
    url: str
    kind: str
    stack_id: str
    item_id: str
    file: str


@dataclass(frozen=True)
class Probe:
    state: str
    http_status: int | None
    detail: str


def changed_stacks(root: Path, changed_paths: list[str]) -> list[Path]:
    selected: set[Path] = set()
    for name in changed_paths:
        parts = Path(name).parts
        if not parts or parts[0] != "content":
            continue
        if len(parts) < 3:
            return stack_folders([root])
        candidate = root / parts[1]
        if candidate.is_dir():
            selected.update(stack_folders([candidate]))
    return sorted(selected)


def collect(selected: list[Path]) -> list[Reference]:
    refs: list[Reference] = []
    for stack in selected:
        bank, problems = read_bank(stack)
        if problems:
            raise ContentError(problems)
        for file, question in bank.questions():
            if question.retired is None:
                refs.extend(
                    Reference(s.url, "source", stack.name, question.id, str(file))
                    for s in question.sources
                )
        for version in version_folders([stack]):
            folder, problems = read_folder(version, (bank, []))
            if problems:
                raise ContentError(problems)
            if folder is not None:
                refs.extend(
                    Reference(m.url, "material", stack.name, m.id, str(version / "syllabus.json"))
                    for m in folder.syllabus.materials
                )
    return refs


def probe(url: str, client: httpx.Client | None = None) -> Probe:
    if client is None:
        with httpx.Client(
            follow_redirects=True,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 (content-link-report)"},
        ) as owned:
            return probe(url, owned)
    for attempt in range(2):
        try:
            status = client.get(url).status_code
            state = (
                "ok"
                if 200 <= status < 300
                else "blocked"
                if status in (401, 403, 429)
                else "broken"
                if 400 <= status < 500
                else "unreachable"
            )
            return Probe(state, status, f"HTTP {status}")
        except httpx.TransportError as exc:
            if attempt:
                return Probe("unreachable", None, type(exc).__name__)
    raise AssertionError("retry loop must return")


def scan(
    refs: list[Reference], checked_at: datetime, check: Callable[[str], Probe] = probe
) -> dict[str, Any]:
    grouped: dict[str, list[Reference]] = defaultdict(list)
    for ref in refs:
        grouped[ref.url].append(ref)
    urls = sorted(grouped)
    with ThreadPoolExecutor(max_workers=16) as pool:
        probes = list(pool.map(check, urls))
    return {
        "checked_at": checked_at.isoformat(),
        "results": [
            {"url": url, **asdict(result), "references": [asdict(r) for r in grouped[url]]}
            for url, result in zip(urls, probes, strict=True)
        ],
    }


def save(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "links.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Content link availability",
        "",
        f"Checked: {report['checked_at']}",
        "",
        "Availability evidence, not factual verification. Blocked checks remain unknown.",
        "",
    ]
    for result in report["results"]:
        lines.append(f"- {result['state']}: {result['url']} ({result['detail']})")
        for ref in result["references"]:
            lines.append(
                f"  - {ref['stack_id']} / {ref['kind']} / {ref['item_id']} / {ref['file']}"
            )
    (output / "links.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--changed-since")
    parser.add_argument("--output", type=Path, default=Path("content-link-results"))
    args = parser.parse_args()
    selected = stack_folders([args.root])
    if args.changed_since:
        diff = subprocess.run(
            ["git", "diff", "--name-only", f"{args.changed_since}...HEAD", "--", str(args.root)],
            check=True,
            capture_output=True,
            text=True,
        )
        selected = changed_stacks(args.root, diff.stdout.splitlines())
    report = scan(collect(selected), datetime.now(UTC))
    save(report, args.output)
    if any(r["state"] in ("broken", "unreachable") for r in report["results"]):
        raise SystemExit(1)
