"use client";

import { Check, Copy, Plug, Trash2 } from "lucide-react";
import { useActionState, useState, useTransition } from "react";
import { Notice } from "@/components/Notice";
import { Spinner } from "@/components/QuestionCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { AccessToken } from "@/lib/api";
import type { TokenState } from "./actions";

const dateFormat = new Intl.DateTimeFormat("en-GB", {
  dateStyle: "medium",
  timeZone: "UTC",
});

const PLACEHOLDER = "<your token>";

/**
 * Personal access tokens for the MCP connector: how to connect, create one (shown once, to
 * copy), see the live ones, and revoke any. Once a token is created, the connect instructions
 * carry it in place of the placeholder, ready to copy.
 */
export function AccessTokens({
  mcpUrl,
  tokens,
  createAction,
  revokeAction,
}: {
  mcpUrl: string;
  tokens: AccessToken[];
  createAction: (previous: TokenState, form: FormData) => Promise<TokenState>;
  revokeAction: (id: number) => Promise<void>;
}) {
  const [state, formAction, pending] = useActionState(createAction, null);
  const [revoking, startRevoking] = useTransition();
  // Shown until the new token is revoked; a reload hides it for good.
  const created =
    state?.ok === true && tokens.some((t) => t.id === state.token.id) ? state.token.token : null;
  const token = created ?? PLACEHOLDER;
  const command = `claude mcp add --transport http chickenkiller ${mcpUrl} --header "Authorization: Bearer ${token}"`;

  return (
    <div className="space-y-4">
      <ol className="list-decimal space-y-1 pl-5 text-sm leading-relaxed text-muted-foreground">
        <li>Create a token below and copy it.</li>
        <li>
          Add a custom connector in your Claude client with the URL <code>{mcpUrl}</code> and the
          header <code>Authorization: Bearer {token}</code>. In Claude Code:
          <span className="mt-1 flex items-start gap-2">
            <pre
              aria-label="Claude Code command"
              className="min-w-0 flex-1 overflow-x-auto rounded-lg bg-muted p-2 text-xs"
            >
              {command}
            </pre>
            {created && <CopyButton text={command} label="Copy command" />}
          </span>
        </li>
        <li>Revoke a token here as soon as you no longer need it.</li>
      </ol>
      <div className="space-y-4 rounded-2xl border bg-card p-5 shadow-xs">
        <form action={formAction} className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="flex-1 space-y-1.5">
            <label htmlFor="token-name" className="text-sm font-semibold">
              Token name
            </label>
            <Input
              id="token-name"
              name="name"
              autoComplete="off"
              placeholder="Claude Desktop"
              className="h-10 bg-background"
            />
          </div>
          <Button type="submit" size="lg" className="h-10 px-4" disabled={pending}>
            {pending ? <Spinner /> : <Plug aria-hidden />}
            Create token
          </Button>
        </form>

        {created && <NewToken token={created} />}
        {state?.ok === false && (
          <Notice tone="error" role="alert">
            {state.message}
          </Notice>
        )}

        {tokens.length === 0 ? (
          <p className="text-sm text-muted-foreground">You have no tokens.</p>
        ) : (
          <ul aria-label="Your tokens" className="divide-y overflow-hidden rounded-xl border">
            {tokens.map((t) => (
              <li key={t.id} className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm">
                <span className="min-w-0 flex-1">
                  <span className="font-medium">{t.name}</span>{" "}
                  <code className="text-xs">{t.prefix}…</code>
                  <span className="block text-xs text-muted-foreground">
                    Created {dateFormat.format(new Date(t.created_at))} ·{" "}
                    {t.last_used_at
                      ? `last used ${dateFormat.format(new Date(t.last_used_at))}`
                      : "never used"}
                  </span>
                </span>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={revoking}
                  aria-label={`Revoke ${t.name}`}
                  onClick={() => startRevoking(() => revokeAction(t.id))}
                >
                  <Trash2 aria-hidden />
                  Revoke
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

/** A token just created: shown once, with a copy button. */
function NewToken({ token }: { token: string }) {
  return (
    <Notice tone="success" role="status">
      <span className="block space-y-2">
        <span className="block font-medium">
          Copy your token now. It won&apos;t be shown again.
        </span>
        <span className="flex flex-wrap items-center gap-2">
          <code className="break-all">{token}</code>
          <CopyButton text={token} label="Copy" />
        </span>
      </span>
    </Notice>
  );
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={() => {
        void navigator.clipboard.writeText(text).then(() => setCopied(true));
      }}
    >
      {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
      {copied ? "Copied" : label}
    </Button>
  );
}
