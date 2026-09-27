import { afterEach, expect, it, vi } from "vitest";
import { saveActiveStacks } from "./actions";

vi.mock("next/cache", () => ({ revalidatePath: () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => vi.unstubAllGlobals());

function form(...stackIds: string[]): FormData {
  const data = new FormData();
  for (const id of stackIds) data.append("stack_ids", id);
  return data;
}

it("saves every ticked Stack as an Active Stack, then lands on the home screen", async () => {
  const fetch = vi.fn(async () => Response.json({}));
  vi.stubGlobal("fetch", fetch);

  const result = saveActiveStacks(null, form("agentic-ai-engineer", "data-engineer"));

  await expect(result).rejects.toThrow(
    expect.objectContaining({ digest: expect.stringContaining(";/;") }),
  );
  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/me/active-stacks",
    expect.objectContaining({
      method: "PUT",
      body: JSON.stringify({ stack_ids: ["agentic-ai-engineer", "data-engineer"] }),
    }),
  );
});

it("asks for at least one Stack without calling the API", async () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);

  expect(await saveActiveStacks(null, form())).toEqual({ error: "Pick at least one Stack." });
  expect(fetch).not.toHaveBeenCalled();
});

it("shows the API's reason when a Stack can't be activated", async () => {
  const detail = "Choose one of the published Stacks.";
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail }, { status: 422 })));

  expect(await saveActiveStacks(null, form("draft-stack"))).toEqual({ error: detail });
});
