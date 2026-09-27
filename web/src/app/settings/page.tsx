import Link from "next/link";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import { Mail, CalendarClock } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { StackSettingsForm } from "@/components/StackSettingsForm";
import { Button } from "@/components/ui/button";
import { api, type Me, type StackSummary } from "@/lib/api";
import { saveActiveStacks } from "./actions";

export default async function SettingsPage() {
  await connection();
  const [me, stackList] = await Promise.all([api<Me>("/me"), api<StackSummary[]>("/stacks")]);
  if (!me || me.needs_onboarding) redirect("/onboarding");

  // A Stack the Admin has since withdrawn is no longer listed, but its Learners may keep it.
  const stacks = stackList ?? [];
  const withdrawn: StackSummary[] = me.active_stacks
    .filter((a) => !stacks.some((s) => s.id === a.id))
    .map((a) => ({ id: a.id, name: a.name, summary: "One of your Active Stacks.", version: "" }));

  return (
    <main className="mx-auto max-w-3xl">
      <PageHeader
        crumbs={<Link href="/">Your Stacks</Link>}
        title="Settings"
        description={
          <p>
            Tick the Stacks you want to study. Your progress on each Stack is kept, so a Stack
            you untick picks up where you left off when you tick it again.
          </p>
        }
      />
      {me.is_admin && (
        <div className="mb-8 flex flex-wrap items-center gap-2 rounded-2xl border bg-muted/40 p-3">
          <span className="px-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            Admin:
          </span>{" "}
          <Button asChild variant="outline" size="sm">
            <Link href="/admin/invitations">
              <Mail aria-hidden />
              Invitations
            </Link>
          </Button>{" "}
          <Button asChild variant="outline" size="sm">
            <Link href="/admin/challenges">
              <CalendarClock aria-hidden />
              Upcoming Challenges
            </Link>
          </Button>
        </div>
      )}
      <StackSettingsForm
        stacks={[...withdrawn, ...stacks]}
        action={saveActiveStacks}
        submitLabel="Save"
        current={me.active_stacks.map((a) => a.id)}
      />
    </main>
  );
}
