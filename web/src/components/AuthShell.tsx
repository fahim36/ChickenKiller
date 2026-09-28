import { Brain, CalendarCheck, Flame, Repeat } from "lucide-react";
import type { ReactNode } from "react";

const POINTS = [
  { icon: CalendarCheck, text: "A new Daily Challenge every day at 00:00 UTC: three Questions, the same for everyone." },
  { icon: Flame, text: "Keep your Streak going and share a Result Card of how you did." },
  { icon: Brain, text: "A researched Syllabus of Weekly Lessons, each ending with a quiz." },
  { icon: Repeat, text: "Review brings Missed Questions back until they stick." },
] as const;

/** The sign-in and sign-up screens: what the app is, next to Clerk's form. */
export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <main className="grid items-center gap-10 lg:grid-cols-[1fr_auto] lg:gap-16 lg:py-10">
      <div className="max-w-xl space-y-6">
        <p className="inline-flex items-center gap-2 rounded-full border bg-card px-3 py-1 text-xs font-medium text-muted-foreground shadow-xs">
          <span className="size-1.5 rounded-full bg-success" aria-hidden />
          Daily interview prep
        </p>
        <h1 className="font-heading text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
          Crack your next interview,{" "}
          <span className="bg-linear-to-r from-primary to-streak bg-clip-text text-transparent">
            one Challenge a day.
          </span>
        </h1>
        <ul className="grid list-none gap-3 p-0">
          {POINTS.map(({ icon: Icon, text }) => (
            <li key={text} className="flex items-start gap-3 text-sm text-muted-foreground sm:text-base">
              <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Icon aria-hidden className="size-4" />
              </span>
              <span className="pt-1">{text}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="order-first flex justify-center lg:order-none lg:justify-end">{children}</div>
    </main>
  );
}
