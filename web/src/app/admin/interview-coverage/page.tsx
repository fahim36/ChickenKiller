import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { api, type Me } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";

export interface InterviewCoverage {
  id: string;
  name: string;
  reviewed_prompts: number;
  covered_concepts: number;
  concepts_without_prompts: string[];
  prompts: {
    id: string;
    concept: string;
    lesson: string;
    version: number;
    unresolved: boolean;
  }[];
}

export default async function InterviewCoveragePage() {
  await connection();
  const me = await api<Me>("/me");
  if (!me?.is_admin) notFound();
  const stacks = await api<InterviewCoverage[]>("/admin/interview-coverage");
  return (
    <main className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="Interview content coverage"
        crumbs={<Link href="/admin/content-health">Content Health</Link>}
        description="Reviewed scenarios by Stack and Concept. This view contains no learner responses."
      />
      {stacks === null ? (
        <p>Coverage could not be loaded. Try again later.</p>
      ) : (
        stacks.map((s) => (
          <section key={s.id}>
            <h2>{s.name}</h2>
            <p>
              {s.reviewed_prompts} reviewed prompts · {s.covered_concepts}{" "}
              covered Concepts
            </p>
            <table>
              <caption>Reviewed interview topics</caption>
              <thead>
                <tr>
                  <th>Prompt</th>
                  <th>Concept</th>
                  <th>Lesson</th>
                  <th>Reference status</th>
                </tr>
              </thead>
              <tbody>
                {s.prompts.map((p) => (
                  <tr key={p.id}>
                    <td>
                      {p.id} · v{p.version}
                    </td>
                    <td>{p.concept}</td>
                    <td>
                      <Link
                        href={`/stacks/${encodeURIComponent(s.id)}/lessons/${encodeURIComponent(p.lesson)}`}
                      >
                        {p.lesson}
                      </Link>
                    </td>
                    <td>
                      {p.unresolved
                        ? "Unresolved teaching reference"
                        : "Resolved"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <details>
              <summary>
                Concepts without interview prompts (
                {s.concepts_without_prompts.length})
              </summary>
              <ul>
                {s.concepts_without_prompts.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </details>
          </section>
        ))
      )}
    </main>
  );
}
