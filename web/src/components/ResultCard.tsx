"use client";

import { useState } from "react";

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
    <div className="result-card">
      <p>
        <output className="result-card-text">{text}</output>
      </p>
      <p className="small muted">✅ correct · ❌ wrong · ⬜ ungraded: couldn&apos;t be graded, no point</p>
      <p>
        <button type="button" onClick={copy}>
          Copy Result Card
        </button>{" "}
        {copied === true && (
          <span role="status" className="small">
            Copied
          </span>
        )}
        {copied === false && (
          <span role="alert" className="small">
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
