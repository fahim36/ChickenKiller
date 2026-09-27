"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

/**
 * A finished Daily Challenge's Result Card, the text the API made ("Agentic AI Engineer #1 · 27
 * Sep · 2/3 ✅❌⬜"), with a button that copies it to share. It never shows the Questions or
 * answers. Copying uses the clipboard API, and falls back to copying a selection where that is
 * missing or refused (an older browser, or a page not served over HTTPS).
 */
export function ResultCard({ text }: { text: string }) {
  const [copied, setCopied] = useState<boolean | null>(null);

  async function copy() {
    setCopied((await copyText(text)) || copyBySelection(text));
  }

  return (
    <div className="space-y-4 rounded-2xl border bg-linear-to-br from-primary/10 via-card to-streak/10 p-5 shadow-xs sm:p-6">
      <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        Result Card
      </p>
      <p>
        <output className="block rounded-xl bg-card px-4 py-3 font-mono text-base font-semibold shadow-xs ring-1 ring-border select-all sm:text-lg">
          {text}
        </output>
      </p>
      <p className="text-xs text-muted-foreground">✅ correct · ❌ wrong · ⬜ ungraded: couldn&apos;t be graded, no point</p>
      <p className="flex flex-wrap items-center gap-3">
        <Button type="button" onClick={copy} variant="outline">
          {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
          Copy Result Card
        </Button>
        {copied === true && (
          <span role="status" className="text-sm font-medium text-success-foreground">
            Copied
          </span>
        )}
        {copied === false && (
          <span role="alert" className="text-sm text-destructive">
            Couldn&apos;t copy it: select the text above and copy it yourself.
          </span>
        )}
      </p>
    </div>
  );
}

async function copyText(text: string): Promise<boolean> {
  if (!navigator.clipboard?.writeText) return false;
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

function copyBySelection(text: string): boolean {
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    area.remove();
  }
}
