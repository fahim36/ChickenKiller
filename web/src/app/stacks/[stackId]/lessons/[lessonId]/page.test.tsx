import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Lesson } from "@/lib/api";
import LessonPage from "./page";

// Outside a real request Next's `connection()` has nothing to wait for.
vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

const lesson: Lesson = {
  id: "w01-l01",
  stack_id: "agentic-ai-engineer",
  week: { id: "w01", number: 1, title: "Python internals" },
  title: "Names, objects and mutability",
  topics: ["`is` vs `==`", "Shallow vs deep copy"],
  exercise: null,
  minutes: 60,
  materials: [
    { id: "fluent-python", title: "Fluent Python", url: "https://example.com/fp", type: "book" },
    { id: "py-docs", title: "Data model", url: "https://example.com/dm", type: "docs" },
  ],
  state: "locked",
  previous_lesson_id: null,
  next_lesson_id: "w01-l02",
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function renderLessonPage(stackId: string, lessonId: string) {
  render(await LessonPage({ params: Promise.resolve({ stackId, lessonId }) } as never));
}

it("shows the Lesson's topics and its Materials with type labels", async () => {
  const fetch = vi.fn(async () => Response.json(lesson));
  vi.stubGlobal("fetch", fetch);

  await renderLessonPage("agentic-ai-engineer", "w01-l01");

  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/stacks/agentic-ai-engineer/lessons/w01-l01",
    expect.anything(),
  );
  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(
    "Names, objects and mutability",
  );
  expect(screen.getAllByRole("listitem").map((li) => li.textContent)).toEqual(
    expect.arrayContaining(["is vs ==", "Shallow vs deep copy"]),
  );
  expect(screen.getByText("Book")).toBeTruthy();
  expect(screen.getByText("Official docs")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Next Lesson →" }).getAttribute("href")).toBe(
    "/stacks/agentic-ai-engineer/lessons/w01-l02",
  );
});

it("lets a Learner read a Locked Lesson and says its quiz waits", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ ...lesson, state: "locked" })));

  await renderLessonPage("agentic-ai-engineer", "w01-l01");

  expect(screen.getByText("Locked")).toBeTruthy();
  expect(screen.getByRole("note").textContent).toBe(
    "You can read ahead. The Lesson Quiz opens once you've completed the Lessons before this one.",
  );
});

it("adds no note to the Unlocked Lesson", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ ...lesson, state: "unlocked" })));

  await renderLessonPage("agentic-ai-engineer", "w01-l01");

  expect(screen.getByText("Unlocked")).toBeTruthy();
  expect(screen.queryByRole("note")).toBeNull();
});

it("is not found when the API has no such Lesson", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 404 })));

  await expect(renderLessonPage("agentic-ai-engineer", "nope")).rejects.toThrow(
    expect.objectContaining({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" }),
  );
});

it("offers the Lesson Quiz on the Unlocked Lesson", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ ...lesson, state: "unlocked" })));

  await renderLessonPage("agentic-ai-engineer", "w01-l01");

  expect(
    screen.getByRole("link", { name: "Start the Lesson Quiz" }).getAttribute("href"),
  ).toBe("/stacks/agentic-ai-engineer/lessons/w01-l01/quiz");
});

it("offers no quiz on a Locked, Completed or Updated Lesson", async () => {
  for (const state of ["locked", "completed", "updated"] as const) {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ ...lesson, state })));
    await renderLessonPage("agentic-ai-engineer", "w01-l01");
    expect(screen.queryByRole("link", { name: "Start the Lesson Quiz" })).toBeNull();
    cleanup();
  }
});

it("says an Updated Lesson's new Questions come in Review", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ ...lesson, state: "updated" })));

  await renderLessonPage("agentic-ai-engineer", "w01-l01");

  expect(screen.getByText("Updated")).toBeTruthy();
  expect(screen.getByRole("note").textContent).toBe(
    "A Syllabus Update added or changed this Lesson after you'd passed it. Its new Questions come in your Review.",
  );
});
