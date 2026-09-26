import { redirect } from "next/navigation";
import { connection } from "next/server";
import { api, type Me } from "@/lib/api";

// Home is the Learner's Active Stack. A first sign-in has none yet, so it goes to onboarding.
export default async function Home() {
  await connection();
  const me = await api<Me>("/me");
  if (!me?.active_stack || me.needs_onboarding) redirect("/onboarding");
  redirect(`/stacks/${encodeURIComponent(me.active_stack.id)}`);
}
