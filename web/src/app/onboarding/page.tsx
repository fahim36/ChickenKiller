import { redirect } from "next/navigation";
import { connection } from "next/server";
import { StackSettingsForm } from "@/components/StackSettingsForm";
import { api, type Me, type StackSummary } from "@/lib/api";
import { saveSettings } from "../settings/actions";

// A Learner's first sign-in lands here (see app/page.tsx and lib/api.ts). It must not call an
// endpoint that needs onboarding, or it would redirect to itself.
export default async function OnboardingPage() {
  await connection();
  const [me, stackList] = await Promise.all([api<Me>("/me"), api<StackSummary[]>("/stacks")]);
  if (me?.active_stack && !me.needs_onboarding) redirect(`/stacks/${me.active_stack.id}`);
  const stacks = stackList ?? [];

  return (
    <main>
      <h1>Pick your Stack</h1>
      <p className="muted">
        Choose what to study and confirm your time zone. You can switch Stacks later in Settings,
        and your progress on each one is kept.
      </p>
      {stacks.length === 0 ? (
        <p className="muted">No Stack is published yet. Ask the Admin to publish one.</p>
      ) : (
        <StackSettingsForm stacks={stacks} action={saveSettings} submitLabel="Start studying" />
      )}
    </main>
  );
}
