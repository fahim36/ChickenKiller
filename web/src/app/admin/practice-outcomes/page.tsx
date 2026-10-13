import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { api, type Me, type PracticeOutcomes } from "@/lib/api";
import { Notice } from "@/components/Notice";
import { PageHeader } from "@/components/PageHeader";

export default async function PracticeOutcomesPage() {
  await connection();
  const me = await api<Me>("/me");
  if (!me?.is_admin) notFound();
  const data = await api<PracticeOutcomes>("/admin/practice-outcomes");
  return (
    <main className="mx-auto max-w-3xl space-y-5">
      <PageHeader
        title="Practice outcomes"
        crumbs={<Link href="/settings">Settings</Link>}
        description="Descriptive results across recorded history, as of now."
      />
      {!data ? (
        <Notice>Practice outcomes couldn&apos;t be loaded. Try again.</Notice>
      ) : (
        <>
          <section aria-label="Delayed performance" className="space-y-2">
            <h2 className="text-lg font-semibold">
              Answers 7–14 days after targeted practice
            </h2>
            {data.qualifying_answers === 0 ? (
              <p>No qualifying answers yet. Accuracy is unavailable.</p>
            ) : (
              <p>
                {Math.round((data.accuracy ?? 0) * 100)}% correct:{" "}
                {data.correct_answers} of {data.qualifying_answers} qualifying
                answers, across {data.learners} learners and {data.concepts}{" "}
                Concepts.
              </p>
            )}
            <p>
              Each Question counts once per learner and Stack. Its first
              recorded answer must be answered and graded; retired Questions and
              Retake answers are excluded. Attribution uses the most recent
              completed targeted Review of the same Concept strictly before the
              answer.
            </p>
          </section>
          <section aria-label="Supporting outcomes" className="space-y-2">
            <h2 className="text-lg font-semibold">Supporting outcomes</h2>
            <p>
              Targeted Review uptake: {data.uptake_days} learner/Stack/Concept
              days across {data.uptake_learners} learners. A loaded due queue
              counts once per day, including reloads; it does not prove practice
              or recommendation effectiveness.
            </p>
            <p>
              Completed targeted practice: {data.completed_practice_answers}{" "}
              answered, graded Review Questions across {data.practice_learners}{" "}
              learners. Each recorded answer is a practice event, regardless of
              correctness.
            </p>
            <p>
              Retakes completed by correct answers: {data.retakes_completed} of{" "}
              {data.retakes_total} recorded Retakes. Content waivers:{" "}
              {data.retakes_waived}, counted separately.
            </p>
          </section>
        </>
      )}
      <Notice>
        Small samples can fluctuate. These results are descriptive, not evidence
        that recommendations caused improvement. The 7–14 day window is an
        evaluation choice, not a validated optimal delay. Challenge replays are
        unrecorded: a first recorded answer does not prove first exposure. This
        is not a mastery or interview-readiness score.
      </Notice>
    </main>
  );
}
