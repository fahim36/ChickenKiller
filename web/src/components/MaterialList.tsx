import type { Material } from "@/lib/api";
import { materialLabel } from "@/lib/format";

export function MaterialList({ materials }: { materials: Material[] }) {
  if (materials.length === 0) return <p className="muted">No Materials for this Lesson.</p>;
  return (
    <ul className="materials">
      {materials.map((m) => (
        <li key={m.id}>
          <span className={`tag tag-${m.type}`}>{materialLabel(m.type)}</span>
          <a href={m.url} target="_blank" rel="noreferrer">
            {m.title}
          </a>
        </li>
      ))}
    </ul>
  );
}
