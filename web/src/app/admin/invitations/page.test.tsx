import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Invitation, Me } from "@/lib/api";
import InvitationsPage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("next/cache", () => ({ revalidatePath: () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

const pending: Invitation[] = [
  { email: "ada@example.com", invited_at: "2026-09-20T10:00:00Z" },
  { email: "grace@example.com", invited_at: "2026-09-21T10:00:00Z" },
];

const ADMIN: Me = { email: "admin@example.com", is_admin: true };

/** The API as this Learner, with these invitations still pending. */
function stubApi(me: Me, invitations: Invitation[] = pending) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.endsWith("/me")) return Response.json(me);
      if (url.endsWith("/invitations")) return Response.json(invitations);
      return new Response(null, { status: 404 });
    }),
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("lets the Admin invite an email address and lists pending invitations", async () => {
  stubApi(ADMIN);

  render(await InvitationsPage());

  expect(screen.getByRole("textbox", { name: "Email address" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Invite" })).toBeTruthy();
  const list = screen.getByRole("list", { name: "Pending invitations" });
  expect(within(list).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
    expect.stringContaining("ada@example.com"),
    expect.stringContaining("grace@example.com"),
  ]);
});

it("says so when no invitation is pending", async () => {
  stubApi(ADMIN, []);

  render(await InvitationsPage());

  expect(screen.getByText("No invitations are pending.")).toBeTruthy();
});

it("is not found for a Learner who isn't the Admin", async () => {
  stubApi({ email: "ada@example.com", is_admin: false });

  await expect(InvitationsPage()).rejects.toThrow(
    expect.objectContaining({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" }),
  );
});
