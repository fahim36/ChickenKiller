import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { AccessToken } from "@/lib/api";
import { AccessTokens } from "./AccessTokens";

afterEach(cleanup);

const MCP = "http://localhost:8000/mcp/";
const TOKEN: AccessToken = {
  id: 7,
  name: "Claude Desktop",
  prefix: "ica_abcdef",
  created_at: "2026-09-27T10:00:00Z",
  last_used_at: null,
};

const command = () => screen.getByLabelText("Claude Code command").textContent;

it("shows a placeholder in the connect command until a token is created", () => {
  render(<AccessTokens mcpUrl={MCP} tokens={[]} createAction={vi.fn()} revokeAction={vi.fn()} />);

  expect(command()).toBe(
    `claude mcp add --transport http chickenkiller ${MCP} --header "Authorization: Bearer <your token>"`,
  );
  expect(screen.queryByRole("button", { name: "Copy command" })).toBeNull();
});

it("fills the new token into the connect command, ready to copy", async () => {
  const createAction = vi.fn(async () => ({
    ok: true as const,
    token: { ...TOKEN, token: "ica_the-new-token" },
  }));
  const { rerender } = render(
    <AccessTokens mcpUrl={MCP} tokens={[]} createAction={createAction} revokeAction={vi.fn()} />,
  );

  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Create token" }));
  });
  rerender(
    <AccessTokens
      mcpUrl={MCP}
      tokens={[TOKEN]}
      createAction={createAction}
      revokeAction={vi.fn()}
    />,
  );

  expect(command()).toContain('--header "Authorization: Bearer ica_the-new-token"');
  expect(screen.getByRole("button", { name: "Copy command" })).toBeTruthy();

  rerender(
    <AccessTokens mcpUrl={MCP} tokens={[]} createAction={createAction} revokeAction={vi.fn()} />,
  );
  expect(command()).toContain("Bearer <your token>");
});
