import Link from "next/link";
import { connection } from "next/server";
import { api, type Me } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { InterviewPractice } from "./InterviewPractice";
import type { InterviewSession, Topics } from "./types";

export default async function InterviewsPage({
  searchParams,
}: {
  searchParams: Promise<{ stack?: string }>;
}) {
  await connection();
  const me = await api<Me>("/me");
  const query = await searchParams;
  const stack =
    me?.active_stacks.find((s) => s.id === query.stack) ?? me?.active_stacks[0];
  const [topics, history] = stack
    ? await Promise.all([
        api<Topics>(
          `/stacks/${encodeURIComponent(stack.id)}/interviews/topics`,
        ),
        api<InterviewSession[]>("/me/interviews"),
      ])
    : [null, null];
  return (
    <main className="mx-auto max-w-3xl">
      <PageHeader
        title="Mock interviews"
        description="Explain your reasoning and practise with reviewed guidance."
      />
      <nav aria-label="Practice Stack">
        {me?.active_stacks.map((s) => (
          <Link
            key={s.id}
            href={`/interviews?stack=${encodeURIComponent(s.id)}`}
            className="mr-4"
          >
            {s.name}
          </Link>
        ))}
      </nav>
      {stack && topics && history ? (
        <InterviewPractice
          key={stack.id}
          stack={stack.id}
          topics={topics}
          history={history}
        />
      ) : (
        <p>
          {stack
            ? "Practice could not be loaded. Reload to try again."
            : "Choose an Active Stack in Settings first."}
        </p>
      )}
    </main>
  );
}
