import { CircleAlert, CircleCheck, Info, TriangleAlert } from "lucide-react";
import type { AriaRole, ReactNode } from "react";
import { cn } from "@/lib/utils";

export type NoticeTone = "info" | "success" | "warning" | "error";

const TONES: Record<NoticeTone, string> = {
  info: "border-primary/20 bg-accent/60 text-accent-foreground",
  success: "border-success/30 bg-success/10 text-success-foreground",
  warning: "border-warning/40 bg-warning/10 text-warning-foreground",
  error: "border-destructive/30 bg-destructive/10 text-destructive",
};

const ICONS = { info: Info, success: CircleCheck, warning: TriangleAlert, error: CircleAlert };

/**
 * A boxed message: what happened, or what to do next. `role` is passed through ("status" for a
 * result, "alert" for an error, "note" for an aside), so screen readers hear it as before.
 */
export function Notice({
  tone = "info",
  role,
  children,
  className,
  as: Tag = "div",
}: {
  tone?: NoticeTone;
  role?: AriaRole;
  children: ReactNode;
  className?: string;
  as?: "div" | "p";
}) {
  const Icon = ICONS[tone];
  return (
    <Tag
      role={role}
      className={cn(
        "flex gap-3 rounded-xl border px-4 py-3 text-sm leading-relaxed [&_a]:font-medium [&_a]:underline [&_a]:underline-offset-4",
        TONES[tone],
        className,
      )}
    >
      <Icon aria-hidden className="mt-0.5 size-4 shrink-0" />
      <span className="min-w-0 flex-1 space-y-2 [&_p]:m-0">{children}</span>
    </Tag>
  );
}
