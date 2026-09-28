import { afterEach, expect, it, vi } from "vitest";
import { deleteStackRequest, requestStack, saveActiveStacks } from "./actions";

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
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => Response.json({ detail }, { status: 422 })),
  );

  expect(await saveActiveStacks(null, form("draft-stack"))).toEqual({ error: detail });
});

function stackForm(fields: Record<string, string>): FormData {
  const data = new FormData();
  for (const [name, value] of Object.entries(fields)) data.append(name, value);
  return data;
}

it("requests a new Stack, then lands on the Stacks screen's build list", async () => {
  const fetch = vi.fn(async () => Response.json({}, { status: 201 }));
  vi.stubGlobal("fetch", fetch);

  const result = requestStack(
    null,
    stackForm({ id: " Data-Engineer ", name: "Data Engineer", summary: "Pipelines.", weeks: "8" }),
  );

  await expect(result).rejects.toThrow(
    expect.objectContaining({
      digest: expect.stringContaining("/stacks?requested=data-engineer#building"),
    }),
  );
  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/stack-requests",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        id: "data-engineer",
        name: "Data Engineer",
        summary: "Pipelines.",
        audience: "",
        weeks: 8,
        notes: "",
      }),
    }),
  );
});

it("asks for the required fields without calling the API, keeping what was typed", async () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);

  const state = await requestStack(null, stackForm({ name: "Data Engineer" }));

  expect(state?.error).toMatch(/id, a name and a one-line summary/);
  expect(state?.values.name).toBe("Data Engineer");
  expect(fetch).not.toHaveBeenCalled();
});

it("shows the API's reason when the Stack can't be requested", async () => {
  const detail = "'data-engineer' is already requested.";
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => Response.json({ detail }, { status: 422 })),
  );

  const state = await requestStack(
    null,
    stackForm({ id: "data-engineer", name: "Data Engineer", summary: "Pipelines." }),
  );

  expect(state?.error).toBe(detail);
});

it("deletes a Stack being built", async () => {
  const fetch = vi.fn(async () => new Response(null, { status: 204 }));
  vi.stubGlobal("fetch", fetch);

  await deleteStackRequest("data-engineer");

  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/stack-requests/data-engineer",
    expect.objectContaining({ method: "DELETE" }),
  );
});
