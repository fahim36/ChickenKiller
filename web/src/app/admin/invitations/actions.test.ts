import { afterEach, expect, it, vi } from "vitest";
import { invite } from "./actions";

vi.mock("next/cache", () => ({ revalidatePath: () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => vi.unstubAllGlobals());

function form(email: string): FormData {
  const data = new FormData();
  data.set("email", email);
  return data;
}

it("invites the email address through the API", async () => {
  const fetch = vi.fn(async () =>
    Response.json({ email: "ada@example.com", invited_at: "2026-09-26T10:00:00Z" }, { status: 201 }),
  );
  vi.stubGlobal("fetch", fetch);

  const result = await invite(null, form(" ada@example.com "));

  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/invitations",
    expect.objectContaining({ method: "POST", body: JSON.stringify({ email: "ada@example.com" }) }),
  );
  expect(result).toEqual({
    ok: true,
    message: "Invited ada@example.com. They can sign in now.",
  });
});

it("shows why the API refused the invitation", async () => {
  const detail = "ada@example.com is already invited.";
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail }, { status: 409 })));

  expect(await invite(null, form("ada@example.com"))).toEqual({ ok: false, message: detail });
});

it("asks for a real email address when the API rejects it", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => Response.json({ detail: [{ msg: "Value error" }] }, { status: 422 })),
  );

  expect(await invite(null, form("nope"))).toEqual({
    ok: false,
    message: "Enter an email address, such as name@example.com.",
  });
});
