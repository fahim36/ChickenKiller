"""Saved link evidence deduplicates Sources/Materials and survives failed probes."""

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.content import link_report
from tests.conftest import ContentFactory


def test_bank_only_changes_select_the_stack_and_collect_sources(
    make_content: ContentFactory,
) -> None:
    folder = make_content()
    root = folder.parent.parent
    selected = link_report.changed_stacks(root, ["content/mini-stack/question-bank/w01-l01.json"])
    assert selected == [folder.parent]
    refs = link_report.collect(selected)
    assert any(r.kind == "source" and r.item_id == "w01-l01-q01" for r in refs)
    assert any(r.kind == "material" and r.item_id == "mat-docs" for r in refs)
    assert link_report.changed_stacks(root, ["web/src/app/page.tsx"]) == []


@pytest.mark.parametrize(
    "status,state",
    [
        (200, "ok"),
        (401, "blocked"),
        (403, "blocked"),
        (429, "blocked"),
        (404, "broken"),
        (410, "broken"),
        (503, "unreachable"),
    ],
)
def test_http_status_is_evidence_not_a_truth_claim(status: int, state: str) -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status)))
    with client:
        result = link_report.probe("https://example.com", client)
    assert result.state == state
    assert result.http_status == status


def test_redirects_are_followed_and_transport_failures_retry() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if len(requests) == 1:
            raise httpx.ConnectError("Transient")
        if request.url.path == "/old":
            return httpx.Response(302, headers={"location": "/new"})
        return httpx.Response(200)

    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        result = link_report.probe("https://example.com/old", client)
    assert result.state == "ok"
    assert requests == [
        "https://example.com/old",
        "https://example.com/old",
        "https://example.com/new",
    ]


def test_exhausted_transport_retry_is_unknown_availability() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ConnectError("Unavailable")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = link_report.probe("https://example.com", client)
    assert result == link_report.Probe("unreachable", None, "ConnectError")
    assert len(calls) == 2


def test_redirect_loop_is_saved_as_unreachable_not_an_aborted_scan() -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(302, headers={"location": "/loop"})
        ),
        follow_redirects=True,
        max_redirects=2,
    ) as client:
        result = link_report.probe("https://example.com/loop", client)
    assert result == link_report.Probe("unreachable", None, "TooManyRedirects")


def test_duplicate_urls_are_probed_once_and_failed_results_are_saved(tmp_path: Path) -> None:
    refs = [
        link_report.Reference("https://example.com/dead", "source", "s", "q1", "bank.json"),
        link_report.Reference("https://example.com/dead", "material", "s", "m1", "syllabus.json"),
    ]
    calls = []

    def fake_probe(url: str) -> link_report.Probe:
        calls.append(url)
        return link_report.Probe("broken", 404, "HTTP 404")

    report = link_report.scan(refs, datetime(2026, 10, 11, tzinfo=UTC), fake_probe)
    assert len(calls) == 1
    assert len(report["results"][0]["references"]) == 2
    link_report.save(report, tmp_path)
    assert (tmp_path / "links.json").is_file()
    assert "404" in (tmp_path / "links.md").read_text()
    assert "not factual verification" in (tmp_path / "links.md").read_text()
