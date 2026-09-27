"use client";

import { Check, Copy, Plug, Trash2 } from "lucide-react";
import { useActionState, useState, useTransition } from "react";
import { Notice } from "@/components/Notice";
import { Spinner } from "@/components/QuestionCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { AccessToken } from "@/lib/api";
import type { TokenState } from "./actions";

const dateFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "UTC" });

/**
 * Personal access tokens for the MCP connector: create one (shown once, to copy), see the
 * live ones, and revoke any.
 */
export function AccessTokens({
  tokens,
  createAction,
  revokeAction,
}: {
  tokens: AccessToken[];
  createAction: (previous: TokenState, form: FormData) => Promise<TokenState>;
  revokeAction: (id: number) => Promise<void>;
}) {
  const [state, formAction, pending] = useActionState(createAction, null);
  const [revoking, startRevoking] = useTransition();

  return (
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

      {/* Shown until the new token is revoked; a reload hides it for good. */}
      {state?.ok === true && tokens.some((t) => t.id === state.token.id) && (
        <NewToken token={state.token.token} />
      )}
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
  );
}

/** A token just created: shown once, with a copy button. */
function NewToken({ token }: { token: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Notice tone="success" role="status">
      <span className="block space-y-2">
        <span className="block font-medium">
          Copy your token now. It won&apos;t be shown again.
        </span>
        <span className="flex flex-wrap items-center gap-2">
          <code className="break-all">{token}</code>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              void navigator.clipboard.writeText(token).then(() => setCopied(true));
            }}
          >
            {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
            {copied ? "Copied" : "Copy"}
          </Button>
        </span>
      </span>
    </Notice>
  );
}
