import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Notice } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";
import { api, type Me } from "@/lib/api";

export interface StackHealth {
  id: string;
  name: string;
  syllabus_version: string | null;
  active_questions: number;
  retired_questions: number;
  thin_concepts: number;
  retired_only_concepts: number;
  untested_concepts: number;
  without_current_lesson: number;
  unresolved_reports: number;
  source_urls: number;
  concepts: {
    id: string;
    name: string;
    active_questions: number;
    multiple_choice: number;
    multiple_select: number;
    legacy_written: number;
    status: string;
  }[];
  lessons: {
    id: string;
    title: string;
    active_questions: number;
    multiple_choice: number;
    multiple_select: number;
    legacy_written: number;
    quiz_eligible: boolean;
  }[];
  sources: {
    url: string;
    title: string;
    oldest_accessed: string;
    latest_accessed: string;
    questions: number;
  }[];
}

export default async function ContentHealthPage() {
  await connection();
  const me = await api<Me>("/me");
  if (!me?.is_admin) notFound();
  const stacks = await api<StackHealth[]>("/admin/content-health");
  return (
    <main className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        crumbs={<Link href="/settings">Settings</Link>}
        title="Content Health"
        description={
          <p>
            Maintenance evidence from imported content. Four Questions per
            Concept is an enrichment target; the publishing minimum remains two.
          </p>
        }
      />
      <nav
        className="flex flex-wrap gap-4 underline"
        aria-label="Content maintenance"
      >
        <Link href="/admin/question-reports">Question Reports</Link>
        <Link href="/admin/challenges">Upcoming Challenges</Link>
        <Link href="/admin/interview-coverage">Interview coverage</Link>
        <a href="https://github.com/fahim36/ChickenKiller/actions/workflows/content-links.yml">
          Saved link-check reports in Actions
        </a>
      </nav>
      <p>
        Actions reports check committed repository links. Their check timestamps
        are separate from original Source access dates and do not verify factual
        claims. Open a saved report to see availability; this page does not
        probe links.
      </p>
      {stacks === null ? (
        <Notice tone="error">
          Content health is unavailable. Try again later.
        </Notice>
      ) : stacks.length === 0 ? (
        <Notice>No Stacks are imported yet.</Notice>
      ) : (
        stacks.map((s) => (
          <section
            key={s.id}
            className="space-y-4 rounded-2xl border bg-card p-5"
          >
            <h2 className="text-xl font-semibold">{s.name}</h2>
            <p>
              Current Syllabus: {s.syllabus_version ?? "none"}.{" "}
              {s.active_questions} active Questions; {s.retired_questions}{" "}
              retired.
            </p>
            <p>
              {s.thin_concepts} thin Concepts (1–3 active Questions);{" "}
              {s.retired_only_concepts} retired-only; {s.untested_concepts}{" "}
              untested.
            </p>
            <p>
              {s.without_current_lesson} active Questions without a current
              Lesson. {s.unresolved_reports} unresolved reports (Open or
              Accepted).
            </p>
            <details>
              <summary className="cursor-pointer font-medium">
                Concept coverage ({s.concepts.length})
              </summary>
              <ul className="mt-3 space-y-2">
                {s.concepts.map((c) => (
                  <li key={c.id}>
                    {c.name} ({c.id}): {c.active_questions} active —{" "}
                    {c.multiple_choice} MC, {c.multiple_select} MS,{" "}
                    {c.legacy_written} legacy written;{" "}
                    {c.status.replaceAll("_", " ")}.
                  </li>
                ))}
              </ul>
            </details>
            <details>
              <summary className="cursor-pointer font-medium">
                Current Lesson quiz composition
              </summary>
              <p className="mt-3">
                Eligibility requires at least eight active Questions, four MC
                and two MS or legacy written Questions.
              </p>
              <ul className="mt-3 space-y-2">
                {s.lessons.map((l) => (
                  <li key={l.id}>
                    {l.title} ({l.id}): {l.active_questions} active —{" "}
                    {l.multiple_choice} MC, {l.multiple_select} MS,{" "}
                    {l.legacy_written} legacy written;{" "}
                    {l.quiz_eligible ? "quiz eligible" : "below quiz minimum"}.
                  </li>
                ))}
              </ul>
            </details>
            <details>
              <summary className="cursor-pointer font-medium">
                Original Source access dates ({s.sources.length} oldest URL
                groups of {s.source_urls})
              </summary>
              <p className="mt-3">
                Original research dates, not revalidation dates. Counts include
                active Questions only.
              </p>
              <ul className="mt-3 space-y-2">
                {s.sources.map((source) => (
                  <li key={source.url}>
                    <a className="underline" href={source.url}>
                      {source.title}
                    </a>
                    : {source.oldest_accessed} to {source.latest_accessed};{" "}
                    {source.questions} Questions.
                  </li>
                ))}
              </ul>
            </details>
          </section>
        ))
      )}
    </main>
  );
}
