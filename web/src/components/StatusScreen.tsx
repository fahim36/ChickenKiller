import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

/**
 * A full-page message when the app can't go on: who can't get in, or a sign-in that failed.
 * These pages must not call the API (lib/api.ts), so this is plain markup.
 */
export function StatusScreen({
  icon: Icon,
  title,
  children,
  action,
  footnote,
}: {
  icon: LucideIcon;
  title: string;
  children: ReactNode;
  action: ReactNode;
  footnote?: ReactNode;
}) {
  return (
    <main className="mx-auto flex max-w-lg flex-col items-center gap-5 rounded-3xl border bg-card px-6 py-12 text-center shadow-xs sm:px-10">
      <span className="flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <Icon aria-hidden className="size-7" />
      </span>
      <h1 className="font-heading text-2xl font-semibold tracking-tight text-balance">{title}</h1>
      <p className="text-muted-foreground">{children}</p>
      <div>{action}</div>
      {footnote && <p className="text-sm text-muted-foreground">{footnote}</p>}
    </main>
  );
}
