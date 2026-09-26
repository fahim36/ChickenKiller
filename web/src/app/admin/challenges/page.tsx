import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { api, type ChallengesAhead, type Me } from "@/lib/api";

const dateFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "UTC" });

/** "Challenges written through 3 Oct 2026 (7 Days left)", as the content check says it. */
function aheadLine(a: ChallengesAhead): string {
  const days = `${a.days_left} Day${a.days_left === 1 ? "" : "s"} left`;
  if (a.written_through === null) return `No Challenges written (${days})`;
  return `Challenges written through ${dateFormat.format(new Date(a.written_through))} (${days})`;
}

// Admin only. The API refuses non-Admins too; this check just keeps the screen out of sight.
export default async function ChallengesPage() {
  await connection();
  const me = await api<Me>("/me");
  if (!me?.is_admin) notFound();
  const stacks = (await api<ChallengesAhead[]>("/admin/challenges")) ?? [];

  return (
    <main>
      <p className="crumbs">
        <Link href="/settings">Settings</Link> · <Link href="/admin/invitations">Invitations</Link>
      </p>
      <h1 id="challenges-heading">Upcoming Challenges</h1>
      <p className="muted">
        How far ahead each Stack&apos;s Daily Challenges are written, counting from today (UTC). A
        Day with no Challenge written has no Challenge.
      </p>
      {stacks.length === 0 ? (
        <p className="muted">No Stacks are imported yet.</p>
      ) : (
        <ul className="invitations" aria-labelledby="challenges-heading">
          {stacks.map((s) => (
            <li key={s.stack_id}>
              {s.stack_name}: {aheadLine(s)}
              {s.warning && (
                <p className="notice notice-error">
                  Fewer than three Days are left. Write more with{" "}
                  <code>/write-challenges {s.stack_id} 7</code> in Claude Code.
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
