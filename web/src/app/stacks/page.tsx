import { Plus } from "lucide-react";
import Link from "next/link";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import { PageHeader, Section } from "@/components/PageHeader";
import { StackSettingsForm } from "@/components/StackSettingsForm";
import { Button } from "@/components/ui/button";
import { api, type Me, type StackPlan, type StackSummary } from "@/lib/api";
import { deleteStackRequest, saveActiveStacks } from "./actions";
import { StacksBeingBuilt } from "./StacksBeingBuilt";

/**
 * The Stacks screen: activate and deactivate Stacks. Onboarding asks the same thing the first
 * time; this is where a Learner changes it later. A deactivated Stack keeps its progress.
 * Below, the Stacks being built (Add a Stack), with how far Claude has got.
 */
export default async function StacksPage({ searchParams }: Partial<PageProps<"/stacks">> = {}) {
  await connection();
  const [me, stackList, building, query] = await Promise.all([
    api<Me>("/me"),
    api<StackSummary[]>("/stacks"),
    api<StackPlan[]>("/stack-requests"),
    searchParams,
  ]);
  const requested = typeof query?.requested === "string" ? query.requested : undefined;
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
        title="Your Active Stacks"
        description={
          <p>
            Tick the Stacks you want to study. Your progress on each Stack is kept, so a Stack you
            untick picks up where you left off when you tick it again.
          </p>
        }
        actions={
          <Button asChild variant="outline">
            <Link href="/stacks/new">
              <Plus aria-hidden />
              Add a Stack
            </Link>
          </Button>
        }
      />
      <StackSettingsForm
        stacks={[...withdrawn, ...stacks]}
        action={saveActiveStacks}
        submitLabel="Save"
        current={me.active_stacks.map((a) => a.id)}
      />
      {building && building.length > 0 && (
        <Section
          title="Stacks being built"
          id="building"
          description="Requested Stacks: Claude drafts the weekly plan, then the quiz setup, and the Admin makes them live."
        >
          <StacksBeingBuilt
            plans={building}
            requested={requested}
            canDelete={(p) => me.is_admin || p.requested_by === me.email}
            deleteAction={deleteStackRequest}
          />
        </Section>
      )}
    </main>
  );
}
