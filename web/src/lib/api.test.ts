import { afterEach, expect, it, vi } from "vitest";
import { api, ApiError, apiPost } from "./api";

// Clerk is the login provider (ADR-0002): stand in for the signed-in person's session.
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => vi.unstubAllGlobals());

it("sends the signed-in person's session token to the API", async () => {
  const fetch = vi.fn(async () => Response.json([]));
  vi.stubGlobal("fetch", fetch);

  await api("/stacks");

  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/stacks",
    expect.objectContaining({ headers: { Authorization: "Bearer session-token" } }),
  );
});

it("sends a person who wasn't invited to the not-invited page", async () => {
  const detail = { code: "not_invited", message: "This email address hasn't been invited." };
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail }, { status: 403 })));

  await expect(api("/stacks")).rejects.toThrow(
    expect.objectContaining({ digest: expect.stringContaining("/not-invited") }),
  );
});

it("reports other refusals as API errors carrying the API's message", async () => {
  const detail = "Only the Admin can do this.";
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail }, { status: 403 })));

  const error = await apiPost("/invitations", { email: "ada@example.com" }).catch((e) => e);

  expect(error).toBeInstanceOf(ApiError);
  expect(error).toMatchObject({ status: 403, message: "Only the Admin can do this." });
});
