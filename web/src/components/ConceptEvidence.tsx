import Link from "next/link";
import type { ConceptEvidenceItem, StackEvidence } from "@/lib/api";

const LABELS = {
  weak: "Weak Concept",
  recovered: "Recovery rule met",
  expired: "No recent evidence",
  insufficient: "Not enough evidence",
};

/** Counts describe practice evidence; these rules never certify mastery or lock a Lesson. */
export function ConceptEvidence({ evidence }: { evidence: StackEvidence }) {
  const weak = evidence.concepts.filter((c) => c.status === "weak");
  const other = evidence.concepts.filter((c) => c.status !== "weak");
  return (
    <section aria-labelledby="concept-evidence-heading" className="mb-8 space-y-4 rounded-2xl border bg-card p-5">
      <h2 id="concept-evidence-heading" className="font-heading text-lg font-semibold">Concept evidence</h2>
      <p className="text-sm text-muted-foreground">
        As of {evidence.as_of} UTC. Two distinct Questions missed within 30 UTC Days signal a weakness.
        Recovery needs correct answers after the latest miss on three UTC Days across two Questions.
        These counts describe recorded practice; they do not certify interview readiness.
      </p>
      {weak.length === 0 ? <p>No current Weak Concept signal.</p> : (
        <EvidenceList concepts={weak} stackId={evidence.stack_id} />
      )}
      {other.length > 0 && (
        <details className="space-y-4">
          <summary className="cursor-pointer font-medium">Other Concept evidence ({other.length})</summary>
          <EvidenceList concepts={other} stackId={evidence.stack_id} />
        </details>
      )}
      {evidence.concepts.length === 0 && <p>Not enough evidence. Practice will appear here as Questions become available.</p>}
    </section>
  );
}

function EvidenceList({ concepts, stackId }: { concepts: ConceptEvidenceItem[]; stackId: string }) {
  return (
    <ul className="space-y-3">
      {concepts.map((concept) => (
        <li key={concept.id} className="space-y-2 rounded-xl border p-4">
          <h3 className="font-medium">{concept.name}</h3>
          <p className="text-sm font-medium">{LABELS[concept.status]}</p>
          <p className="text-sm text-muted-foreground">
            {concept.recent_missed_questions} distinct Questions missed in the current and preceding 29 UTC Days.
            {concept.latest_miss && <> Latest miss: {concept.latest_miss.slice(0, 10)} UTC.</>}
          </p>
          {(concept.status === "weak" || concept.status === "recovered") && (
            <p className="text-sm">
              Correct since the latest miss: {concept.recovery_days} of 3 UTC Days,
              {" "}{concept.recovery_questions} distinct Questions (2 required).
            </p>
          )}
          {concept.status === "expired" && <p className="text-sm">Earlier evidence left the window; this does not indicate recovery.</p>}
          <p className="text-sm text-muted-foreground">{concept.active_questions} active Questions available.</p>
          {concept.lesson_id ? (
            <Link className="text-sm font-medium underline underline-offset-4"
              href={`/stacks/${encodeURIComponent(stackId)}/lessons/${encodeURIComponent(concept.lesson_id)}`}>
              Read {concept.lesson_title ?? "the teaching Lesson"}
            </Link>
          ) : <p className="text-sm text-muted-foreground">No teaching Lesson is available in the current Syllabus.</p>}
        </li>
      ))}
    </ul>
  );
}
