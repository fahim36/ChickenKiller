import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Inline } from "@/components/Inline";
import { api, type Syllabus } from "@/lib/api";
import { formatMinutes, weekMinutes } from "@/lib/format";

export default async function SyllabusPage({ params }: PageProps<"/stacks/[stackId]">) {
  await connection();
  const { stackId } = await params;
  const syllabus = await api<Syllabus>(`/stacks/${encodeURIComponent(stackId)}`);
  if (!syllabus) notFound();

  return (
    <main>
      <p className="crumbs">
        <Link href="/">Stacks</Link>
      </p>
      <h1>{syllabus.name}</h1>
      <p className="muted">
        {syllabus.summary} · Syllabus {syllabus.version}
      </p>

      {syllabus.weeks.map((week) => (
        <section key={week.id} className="week">
          <h2>
            Week {week.number}: {week.title}{" "}
            <span className="muted small">{formatMinutes(weekMinutes(week))}</span>
          </h2>
          <p>{week.goal}</p>
          <ol className="lessons">
            {week.lessons.map((lesson) => (
              <li key={lesson.id}>
                <Link href={`/stacks/${syllabus.id}/lessons/${lesson.id}`}>
                  <Inline text={lesson.title} />
                </Link>
              </li>
            ))}
          </ol>
          {week.milestones.length > 0 && (
            <ul className="milestones">
              {week.milestones.map((m) => (
                <li key={m.id}>
                  <span className={`tag tag-${m.kind}`}>
                    {m.kind === "build" ? "Build" : "Job hunt"}
                  </span>
                  {m.title}
                </li>
              ))}
            </ul>
          )}
          <p className="small">
            <strong>Deliverable:</strong> {week.deliverable}
          </p>
        </section>
      ))}
    </main>
  );
}
