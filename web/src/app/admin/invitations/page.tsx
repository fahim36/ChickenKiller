import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Clock, Mail } from "lucide-react";
import { Notice } from "@/components/Notice";
import { PageHeader, Section } from "@/components/PageHeader";
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
    <main className="mx-auto max-w-3xl">
      <PageHeader
        crumbs={
          <>
            <Link href="/settings">Settings</Link> ·{" "}
            <Link href="/admin/challenges">Upcoming Challenges</Link>
          </>
        }
        title="Invitations"
        description={
          <p>
            Invite someone by email. They sign in with that address, by email or Google, and
            become a Learner.
          </p>
        }
      />

      <InviteForm action={invite} />

      <Section title="Pending invitations" id="pending-heading">
        {invitations.length === 0 ? (
          <Notice>No invitations are pending.</Notice>
        ) : (
          <ul
            className="divide-y overflow-hidden rounded-2xl border bg-card shadow-xs"
            aria-labelledby="pending-heading"
          >
            {invitations.map((i) => (
              <li key={i.email} className="flex items-center gap-3 px-4 py-3">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Mail aria-hidden className="size-4" />
                </span>
                <span className="min-w-0 flex-1 truncate font-medium">{i.email}</span>{" "}
                <span className="inline-flex shrink-0 items-center gap-1 text-xs text-muted-foreground">
                  <Clock aria-hidden className="size-3.5" />
                  invited {dateFormat.format(new Date(i.invited_at))}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </main>
  );
}
