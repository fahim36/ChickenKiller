import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Grading } from "@/lib/api";
import { NEW_LEARNER, ONBOARDED, stubApi } from "@/test/stubApi";
import SettingsPage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("next/headers", () => ({
  cookies: async () => ({ get: () => undefined }),
}));
vi.mock("next/cache", () => ({ revalidatePath: () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const NO_KEY: Grading = {
  key: null,
  grader: "server",
  keys_enabled: true,
  default_model: "gemini-3.1-flash-lite",
  own_key_required: false,
};

it("explains grading and offers a key field, never a saved key", async () => {
  stubApi({ "/me": ONBOARDED, "/me/grading": NO_KEY, "/me/access-tokens": [] });

  render(await SettingsPage());

  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Settings");
  expect(screen.getByRole("heading", { name: "Grading" })).toBeTruthy();
  expect(screen.getByLabelText("Gemini API key").getAttribute("type")).toBe("password");
  expect(screen.getByRole("link", { name: "Google AI Studio" })).toBeTruthy();
  expect(screen.getByText(/Set your own Gemini key/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "your Active Stacks" }).getAttribute("href")).toBe(
    "/stacks",
  );
  expect(screen.queryAllByRole("checkbox")).toEqual([]);
});

it("asks for the Learner's own key when no other grader is used", async () => {
  stubApi({
    "/me": ONBOARDED,
    "/me/grading": { ...NO_KEY, grader: "none", own_key_required: true },
    "/me/access-tokens": [],
  });

  render(await SettingsPage());

  expect(screen.getByText(/without one they can't be graded/)).toBeTruthy();
  expect(screen.getByText(/Set your own Gemini key/)).toBeTruthy();
  expect(screen.queryByText(/server's Claude Code/)).toBeNull();
});

it("shows only the saved key's last four characters", async () => {
  stubApi({
    "/me": ONBOARDED,
    "/me/grading": {
      ...NO_KEY,
      grader: "own_key",
      key: {
        provider: "gemini",
        model: NO_KEY.default_model,
        key_hint: "WXYZ",
        updated_at: "2026-09-27T10:00:00Z",
      },
    },
    "/me/access-tokens": [],
  });

  render(await SettingsPage());

  expect(screen.getByText("WXYZ")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Remove key" })).toBeTruthy();
  expect(screen.getByLabelText("Replace your Gemini API key")).toBeTruthy();
});

it("hides a key saved for NVIDIA and asks for a Gemini key", async () => {
  stubApi({
    "/me": ONBOARDED,
    "/me/grading": {
      ...NO_KEY,
      grader: "own_key",
      key: {
        provider: "nvidia",
        model: "nvidia/nemotron-3.5-lightning-30b-a3b",
        key_hint: "WXYZ",
        updated_at: "2026-09-27T10:00:00Z",
      },
    },
    "/me/access-tokens": [],
  });

  render(await SettingsPage());

  expect(screen.queryByText(/NVIDIA/)).toBeNull();
  expect(screen.queryByText("WXYZ")).toBeNull();
  expect(screen.getByText(/Set your own Gemini key/)).toBeTruthy();
  expect(screen.getByLabelText("Gemini API key")).toBeTruthy();
  expect((screen.getByLabelText(/^Model/) as HTMLInputElement).value).toBe(
    "gemini-3.1-flash-lite",
  );
});

it("says so when the server can't store keys", async () => {
  stubApi({
    "/me": ONBOARDED,
    "/me/grading": { ...NO_KEY, keys_enabled: false },
    "/me/access-tokens": [],
  });

  render(await SettingsPage());

  expect(screen.queryByLabelText("Gemini API key")).toBeNull();
  expect(screen.getByRole("note").textContent).toContain("LLM_KEY_SECRET");
});

it("lists the Learner's connector tokens, each revocable", async () => {
  stubApi({
    "/me": ONBOARDED,
    "/me/grading": NO_KEY,
    "/me/access-tokens": [
      {
        id: 3,
        name: "Claude Desktop",
        prefix: "ica_abcdef",
        created_at: "2026-09-27T10:00:00Z",
        last_used_at: null,
      },
    ],
  });

  render(await SettingsPage());

  expect(screen.getByRole("heading", { name: "Claude connector (MCP)" })).toBeTruthy();
  expect(screen.getByText("Claude Desktop")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Revoke Claude Desktop" })).toBeTruthy();
  expect(screen.getAllByText(/http:\/\/localhost:8000\/mcp\//).length).toBeGreaterThan(0);
});

it("shows the Admin the way to the Admin screens", async () => {
  stubApi({
    "/me": { ...ONBOARDED, is_admin: true },
    "/me/grading": NO_KEY,
    "/me/access-tokens": [],
  });

  render(await SettingsPage());

  for (const [name, href] of [
    ["Invitations", "/admin/invitations"],
    ["Upcoming Challenges", "/admin/challenges"],
    ["Drafts", "/admin/drafts"],
  ]) {
    expect(screen.getByRole("link", { name }).getAttribute("href")).toBe(href);
  }
});

it("sends a Learner who hasn't onboarded to onboarding", async () => {
  stubApi({
    "/me": NEW_LEARNER,
    "/me/grading": NO_KEY,
    "/me/access-tokens": [],
  });

  await expect(SettingsPage()).rejects.toThrow(
    expect.objectContaining({ digest: expect.stringContaining("/onboarding") }),
  );
});
