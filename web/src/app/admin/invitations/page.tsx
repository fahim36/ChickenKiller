import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { api, type Invitation, type Me } from "@/lib/api";
import { invite } from "./actions";
import { InviteForm } from "./InviteForm";

const dateFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "UTC" });

// Admin only. The API refuses non-Admins too; this check just keeps the screen out of sight.
export default async function InvitationsPage() {
  await connection();
  const me = await api<Me>("/me");
  if (!me?.is_admin) notFound();
  const invitations = (await api<Invitation[]>("/invitations")) ?? [];

  return (
    <main>
      <p className="crumbs">
        <Link href="/settings">Settings</Link> ·{" "}
        <Link href="/admin/challenges">Upcoming Challenges</Link>
      </p>
      <h1>Invitations</h1>
      <p className="muted">
        Invite someone by email. They sign in with that address, by email or Google, and become a
        Learner.
      </p>

      <InviteForm action={invite} />

      <h2 id="pending-heading">Pending invitations</h2>
      {invitations.length === 0 ? (
        <p className="muted">No invitations are pending.</p>
      ) : (
        <ul className="invitations" aria-labelledby="pending-heading">
          {invitations.map((i) => (
            <li key={i.email}>
              {i.email}{" "}
              <span className="muted small">invited {dateFormat.format(new Date(i.invited_at))}</span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
