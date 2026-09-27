import { afterEach, expect, it, vi } from "vitest";
import { api, ApiError, apiPost, apiPostGraded, apiPut } from "./api";

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
    expect.objectContaining({
      headers: { Authorization: "Bearer session-token" },
    }),
  );
});

it("sends a person who wasn't invited to the not-invited page", async () => {
  const detail = {
    code: "not_invited",
    message: "This email address hasn't been invited.",
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => Response.json({ detail }, { status: 403 })),
  );

  await expect(api("/stacks")).rejects.toThrow(
    expect.objectContaining({
      digest: expect.stringContaining("/not-invited"),
    }),
  );
});

it("sends a Learner who hasn't onboarded yet to onboarding", async () => {
  const detail = {
    code: "onboarding_needed",
    message: "Pick the Stacks you want to study first.",
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => Response.json({ detail }, { status: 409 })),
  );

  await expect(api("/stacks/agentic-ai-engineer")).rejects.toThrow(
    expect.objectContaining({ digest: expect.stringContaining("/onboarding") }),
  );
});

it("sends a Learner to settings for a Stack that isn't one of their Active Stacks", async () => {
  const detail = {
    code: "not_active_stack",
    message: "This isn't one of your Active Stacks.",
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => Response.json({ detail }, { status: 409 })),
  );

  await expect(api("/stacks/data-engineer")).rejects.toThrow(
    expect.objectContaining({ digest: expect.stringContaining(";/settings;") }),
  );
});

it("sends a person whose sign-in the API couldn't verify to the sign-in-failed page", async () => {
  const detail = "Your sign-in is invalid or has expired.";
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => Response.json({ detail }, { status: 401 })),
  );

  await expect(api("/me")).rejects.toThrow(
    expect.objectContaining({
      digest: expect.stringContaining(";/sign-in-failed;"),
    }),
  );
});

it("sends a person to the sign-in-unavailable page when the API can't check sign-ins", async () => {
  const detail = "Sign-in can't be checked right now. Try again soon.";
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => Response.json({ detail }, { status: 503 })),
  );

  await expect(apiPost("/review", {})).rejects.toThrow(
    expect.objectContaining({
      digest: expect.stringContaining(";/sign-in-unavailable;"),
    }),
  );
});

it("still hands grading failures back to the page, not the sign-in-unavailable page", async () => {
  const detail = {
    code: "grading_failed",
    message: "Grading failed. Submit again.",
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => Response.json({ detail }, { status: 503 })),
  );

  await expect(apiPostGraded("/review/answers", {})).resolves.toEqual(detail);
});

it("PUTs JSON with the session token", async () => {
  const fetch = vi.fn(async () => Response.json({ ok: true }));
  vi.stubGlobal("fetch", fetch);

  expect(
    await apiPut("/me/active-stacks", { stack_ids: ["data-engineer"] }),
  ).toEqual({
    ok: true,
  });
  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/me/active-stacks",
    expect.objectContaining({
      method: "PUT",
      body: JSON.stringify({ stack_ids: ["data-engineer"] }),
      headers: {
        Authorization: "Bearer session-token",
        "Content-Type": "application/json",
      },
    }),
  );
});

it("reports other refusals as API errors carrying the API's message", async () => {
  const detail = "Only the Admin can do this.";
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => Response.json({ detail }, { status: 403 })),
  );

  const error = await apiPost("/invitations", {
    email: "ada@example.com",
  }).catch((e) => e);

  expect(error).toBeInstanceOf(ApiError);
  expect(error).toMatchObject({
    status: 403,
    message: "Only the Admin can do this.",
  });
});
