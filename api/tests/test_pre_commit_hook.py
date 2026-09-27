"""The `content-check` pre-commit hook, run the way pre-commit runs it: the hook's `entry` plus its
`args`, from the repository root. Here the root is a stand-in holding test content."""

import copy
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

import yaml

from app.config import REPO_ROOT
from tests.conftest import API_DIR, BANK, LESSON, SYLLABUS, write_folder


def content_check_hook() -> dict[str, Any]:
    text = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    config: dict[str, Any] = yaml.safe_load(text)
    hook: dict[str, Any]
    [hook] = [h for repo in config["repos"] for h in repo["hooks"] if h["id"] == "content-check"]
    return hook


def run_hook(repo_root: Path) -> subprocess.CompletedProcess[str]:
    hook = content_check_hook()
    command = shlex.split(hook["entry"]) + hook.get("args", [])
    # The entry names the api project relative to the repository root; point it at the real one.
    command = [str(API_DIR) if part == "api" else part for part in command]
    return subprocess.run(command, cwd=repo_root, capture_output=True, text=True, timeout=300)


def repo_with_content(root: Path, bank: dict[str, Any]) -> Path:
    write_folder(root / "content", copy.deepcopy(SYLLABUS), {LESSON: bank})
    return root


def test_hook_runs_on_content_changes_and_checks_the_whole_content_root() -> None:
    hook = content_check_hook()
    assert hook["pass_filenames"] is False
    assert re.search(hook["files"], "content/mini-stack/v2026-01-01/questions/w01-l01.json")
    assert not re.search(hook["files"], "web/app/page.tsx")


def test_hook_passes_valid_content(tmp_path: Path) -> None:
    result = run_hook(repo_with_content(tmp_path, copy.deepcopy(BANK)))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout


def test_hook_refuses_invalid_content_naming_the_file_and_question(tmp_path: Path) -> None:
    bank = copy.deepcopy(BANK)
    bank["questions"][0]["answer"] = "c"  # a choice that doesn't exist

    result = run_hook(repo_with_content(tmp_path, bank))

    assert result.returncode == 1, result.stdout + result.stderr
    [line] = [x for x in result.stdout.splitlines() if x.startswith("ERROR")]
    assert "w01-l01.json" in line
    assert "[w01-l01-q01] answer is not one of the choices" in line
