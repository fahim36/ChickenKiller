import Link from "next/link";
import { connection } from "next/server";
import { api, type StackSummary } from "@/lib/api";

export default async function Home() {
  await connection(); // render per request: content changes on every import
  const stacks = (await api<StackSummary[]>("/stacks")) ?? [];

  return (
    <main>
      <h1>Choose a Stack</h1>
      {stacks.length === 0 ? (
        <p className="muted">
          No Stacks imported yet. Run <code>uv run content-import</code> in <code>api/</code>.
        </p>
      ) : (
        <ul className="cards">
          {stacks.map((s) => (
            <li key={s.id}>
              <Link href={`/stacks/${s.id}`} className="card">
                <strong>{s.name}</strong>
                <span className="muted">{s.summary}</span>
                <span className="version">{s.version}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
