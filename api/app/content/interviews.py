"""Reviewed interview content, independent of quiz Questions and learner evidence."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.content.format import PermanentId, Source, Text


class FollowUp(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: PermanentId
    scenario: Text
    rubric: list[Text] = Field(min_length=1, max_length=8)


class InterviewPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: PermanentId
    stack: PermanentId
    concept: PermanentId
    lesson: PermanentId
    version: int = Field(ge=1)
    scenario: Text
    rubric: list[Text] = Field(min_length=1, max_length=8)
    misconceptions: list[Text] = Field(min_length=1, max_length=8)
    sources: list[Source] = Field(min_length=1)
    follow_ups: list[FollowUp] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def unique_follow_ups(self) -> "InterviewPrompt":
        ids = [item.id for item in self.follow_ups]
        if len(ids) != len(set(ids)):
            raise ValueError("follow-up IDs must be unique")
        return self


def read_prompts(stack_folder: Path) -> list[InterviewPrompt]:
    """Read reviewed files; absence preserves compatibility with older content folders."""
    prompts = [
        InterviewPrompt.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted((stack_folder / "interviews").glob("*.json"))
    ]
    ids = [prompt.id for prompt in prompts]
    if len(ids) != len(set(ids)):
        raise ValueError("interview prompt IDs must be unique within a Stack")
    if any(prompt.stack != stack_folder.name for prompt in prompts):
        raise ValueError("interview prompt Stack must match its folder")
    return prompts


def check_prompts(
    stack_folder: Path, concepts: set[str], lessons: set[str], teaching: set[tuple[str, str]]
) -> list[InterviewPrompt]:
    prompts = read_prompts(stack_folder)
    for prompt in prompts:
        if prompt.concept not in concepts or prompt.lesson not in lessons:
            raise ValueError(f"{prompt.id}: Concept and teaching Lesson must resolve")
        if (prompt.concept, prompt.lesson) not in teaching:
            raise ValueError(f"{prompt.id}: Lesson must teach this Concept")
    return prompts
