import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * The top of a page: optional breadcrumb links, the page's one `h1`, a line saying what the page
 * is for, and actions on the right (on wide screens).
 */
export function PageHeader({
  crumbs,
  title,
  description,
  actions,
  className,
}: {
  crumbs?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("mb-8 flex flex-col gap-4 sm:flex-row sm:items-end", className)}>
      <div className="min-w-0 flex-1 space-y-2">
        {crumbs && <Crumbs>{crumbs}</Crumbs>}
        <h1 className="font-heading text-2xl font-semibold tracking-tight text-balance sm:text-3xl">
          {title}
        </h1>
        {description && (
          <div className="max-w-prose text-sm text-muted-foreground sm:text-base">
            {description}
          </div>
        )}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

/** Breadcrumb links above a page's title. */
export function Crumbs({ children }: { children: ReactNode }) {
  return (
    <p className="text-sm text-muted-foreground [&_a]:font-medium [&_a]:text-foreground/80 [&_a]:underline-offset-4 [&_a:hover]:text-primary [&_a:hover]:underline">
      {children}
    </p>
  );
}

/** A titled block of a page, below its header. */
export function Section({
  title,
  id,
  description,
  children,
  className,
}: {
  title: ReactNode;
  id?: string;
  description?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("mt-10 space-y-4", className)} aria-labelledby={id}>
      <div className="space-y-1">
        <h2 id={id} className="font-heading text-lg font-semibold tracking-tight">
          {title}
        </h2>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {children}
    </section>
  );
}
