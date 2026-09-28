import Link from "next/link";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import { PageHeader } from "@/components/PageHeader";
import { api, type Me } from "@/lib/api";
import { requestStack } from "../actions";
import { NewStackForm } from "./NewStackForm";

/**
 * Add a Stack: request a new one. Claude then builds it through the MCP connector, the weekly
 * plan first and then the quiz setup, and the Admin reviews it before it goes live.
 */
export default async function NewStackPage() {
  await connection();
  const me = await api<Me>("/me");
  if (!me || me.needs_onboarding) redirect("/onboarding");

  return (
    <main className="mx-auto max-w-3xl">
      <PageHeader
        crumbs={<Link href="/stacks">Your Active Stacks</Link>}
        title="Add a Stack"
        description={
          <ol className="list-decimal space-y-1 pl-5">
            <li>Say what the Stack is for.</li>
            <li>
              Claude, through the connector, researches it and drafts the weekly plan: each
              Week&apos;s Lessons, Milestones and Materials.
            </li>
            <li>Then it writes the quiz setup: the Questions for every Lesson.</li>
            <li>The Admin reviews the drafts and makes the Stack live.</li>
          </ol>
        }
      />
      <NewStackForm action={requestStack} />
    </main>
  );
}
