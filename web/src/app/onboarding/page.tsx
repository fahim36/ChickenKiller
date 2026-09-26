import { redirect } from "next/navigation";
import { connection } from "next/server";
import { StackSettingsForm } from "@/components/StackSettingsForm";
import { api, type Me, type StackSummary } from "@/lib/api";
import { saveActiveStacks } from "../settings/actions";

// A Learner's first sign-in lands here (see app/page.tsx and lib/api.ts). It must not call an
// endpoint that needs onboarding, or it would redirect to itself.
export default async function OnboardingPage() {
  await connection();
  const [me, stackList] = await Promise.all([api<Me>("/me"), api<StackSummary[]>("/stacks")]);
  if (me && !me.needs_onboarding) redirect("/");
  const stacks = stackList ?? [];

  return (
    <main>
      <h1>Pick your Stacks</h1>
      <p className="muted">
        Choose one or more Stacks to study. You can add or drop Stacks later in Settings, and
        your progress on each one is kept.
      </p>
      {stacks.length === 0 ? (
        <p className="muted">No Stack is published yet. Ask the Admin to publish one.</p>
      ) : (
        <StackSettingsForm stacks={stacks} action={saveActiveStacks} submitLabel="Start studying" />
      )}
    </main>
  );
}
