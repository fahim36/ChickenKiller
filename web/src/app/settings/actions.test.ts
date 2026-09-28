import { afterEach, expect, it, vi } from "vitest";
import { createAccessToken, saveGradingKey } from "./actions";

vi.mock("next/cache", () => ({ revalidatePath: () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => vi.unstubAllGlobals());

function form(fields: Record<string, string>): FormData {
  const data = new FormData();
  for (const [k, v] of Object.entries(fields)) data.append(k, v);
  return data;
}

it("sends the key to the API to store, with the default model when none is given", async () => {
  const fetch = vi.fn(async () => Response.json({}));
  vi.stubGlobal("fetch", fetch);

  const result = await saveGradingKey(null, form({ api_key: "  AIza-secret  ", model: "" }));

  expect(result?.ok).toBe(true);
  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/me/grading-key",
    expect.objectContaining({
      method: "PUT",
      body: JSON.stringify({ provider: "gemini", api_key: "AIza-secret", model: null }),
    }),
  );
});

it("reports a refused key without throwing", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => Response.json({ detail: "That doesn't look like an API key." }, { status: 422 })),
  );

  const result = await saveGradingKey(null, form({ api_key: "short" }));

  expect(result).toEqual({ ok: false, message: "That doesn't look like an API key." });
});

it("asks for a key before calling the API", async () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);

  expect((await saveGradingKey(null, form({ api_key: " " })))?.ok).toBe(false);
  expect(fetch).not.toHaveBeenCalled();
});

it("returns a new token once, to show", async () => {
  const token = {
    id: 1,
    name: "Claude",
    prefix: "ica_abcdef",
    created_at: "2026-09-27T10:00:00Z",
    last_used_at: null,
    token: "ica_abcdefsecret",
  };
  vi.stubGlobal("fetch", vi.fn(async () => Response.json(token, { status: 201 })));

  expect(await createAccessToken(null, form({ name: "" }))).toEqual({ ok: true, token });
});
