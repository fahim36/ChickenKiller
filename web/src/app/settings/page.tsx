import Link from "next/link";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import { StackSettingsForm } from "@/components/StackSettingsForm";
import { api, type Me, type StackSummary } from "@/lib/api";
import { saveSettings } from "./actions";

export default async function SettingsPage() {
  await connection();
  const [me, stackList] = await Promise.all([api<Me>("/me"), api<StackSummary[]>("/stacks")]);
  if (!me?.active_stack || !me.time_zone || me.needs_onboarding) redirect("/onboarding");
  const { active_stack: active, time_zone: timeZone } = me;

  // A Stack the Admin has since withdrawn is no longer listed, but its Learners may stay on it.
  const stacks = stackList ?? [];
  const choices: StackSummary[] = stacks.some((s) => s.id === active.id)
    ? stacks
    : [{ id: active.id, name: active.name, summary: "Your Active Stack.", version: "" }, ...stacks];

  return (
    <main>
      <p className="crumbs">
        <Link href={`/stacks/${active.id}`}>{active.name}</Link>
        {me.is_admin && (
          <>
            {" "}
            · Admin: <Link href="/admin/invitations">Invitations</Link>
          </>
        )}
      </p>
      <h1>Settings</h1>
      <p className="muted">
        Switch your Active Stack or change your time zone. Your progress on each Stack is kept, so
        switching back picks up where you left off.
      </p>
      <StackSettingsForm
        stacks={choices}
        action={saveSettings}
        submitLabel="Save"
        current={{ active_stack_id: active.id, time_zone: timeZone }}
      />
    </main>
  );
}
