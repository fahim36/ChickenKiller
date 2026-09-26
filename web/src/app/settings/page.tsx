import Link from "next/link";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import { StackSettingsForm } from "@/components/StackSettingsForm";
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
    <main>
      <p className="crumbs">
        <Link href="/">Your Stacks</Link>
        {me.is_admin && (
          <>
            {" "}
            · Admin: <Link href="/admin/invitations">Invitations</Link>
          </>
        )}
      </p>
      <h1>Settings</h1>
      <p className="muted">
        Tick the Stacks you want to study. Your progress on each Stack is kept, so a Stack you
        untick picks up where you left off when you tick it again.
      </p>
      <StackSettingsForm
        stacks={[...withdrawn, ...stacks]}
        action={saveActiveStacks}
        submitLabel="Save"
        current={me.active_stacks.map((a) => a.id)}
      />
    </main>
  );
}
