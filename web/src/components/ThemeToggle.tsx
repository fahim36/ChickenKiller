"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useState } from "react";
import { applyTheme, type Theme } from "@/lib/theme";
import { cn } from "@/lib/utils";

const OPTIONS = [
  { value: "system", label: "System", icon: Monitor },
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
] as const;

/**
 * Picks the colour theme. It applies at once, by setting data-theme on <html>, and is kept in a
 * cookie so the server renders the same theme on the next visit, with no flash.
 */
export function ThemeToggle({ initial }: { initial: Theme }) {
  const [theme, setTheme] = useState<Theme>(initial);

  function choose(next: Theme) {
    setTheme(next);
    applyTheme(next);
  }

  return (
    <div
      role="radiogroup"
      aria-label="Theme"
      className="inline-flex rounded-xl border bg-card p-1 shadow-xs"
    >
      {OPTIONS.map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={theme === value}
          onClick={() => choose(value)}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
            theme === value
              ? "bg-primary text-primary-foreground shadow-xs"
              : "text-muted-foreground hover:bg-muted hover:text-foreground",
          )}
        >
          <Icon aria-hidden className="size-4" />
          {label}
        </button>
      ))}
    </div>
  );
}
