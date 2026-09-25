from app.content.schema import stale_schema_files


def test_committed_json_schema_matches_the_content_format() -> None:
    assert stale_schema_files() == [], "content/schema/ is out of date; run `uv run content-schema`"
