import { CalendarClock, FileStack, Mail } from "lucide-react";
import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import { connection } from "next/server";
import { PageHeader, Section } from "@/components/PageHeader";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import { api, mcpUrl, type AccessToken, type Grading, type Me } from "@/lib/api";
import { parseTheme, THEME_COOKIE } from "@/lib/theme";
import { AccessTokens } from "./AccessTokens";
import { createAccessToken, removeGradingKey, revokeAccessToken, saveGradingKey } from "./actions";
import { GradingKeyForm } from "./GradingKeyForm";

/**
 * Settings: the colour theme, the LLM key that grades the Learner's written answers, and personal access tokens
 * for the MCP connector; for the Admin, links to the Admin screens. Active Stacks are changed
 * on the Stacks screen.
 */
export default async function SettingsPage() {
  await connection();
  const [me, grading, tokens] = await Promise.all([
    api<Me>("/me"),
    api<Grading>("/me/grading"),
    api<AccessToken[]>("/me/access-tokens"),
  ]);
  if (!me || me.needs_onboarding) redirect("/onboarding");
  const theme = parseTheme((await cookies()).get(THEME_COOKIE)?.value);
  const ownKeyOnly = grading?.own_key_required ?? false;

  return (
    <main className="mx-auto max-w-3xl">
      <PageHeader
        crumbs={<Link href="/">Your Stacks</Link>}
        title="Settings"
        description={
          <p>
            How your written answers are graded, and how your Claude connects to the app. To change
            what you study, go to <Link href="/stacks">your Active Stacks</Link>.
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
          </Button>{" "}
          <Button asChild variant="outline" size="sm">
            <Link href="/admin/drafts">
              <FileStack aria-hidden />
              Drafts
            </Link>
          </Button>
        </div>
      )}

      <Section title="Appearance" id="appearance-heading">
        <p className="mb-4 text-sm leading-relaxed text-muted-foreground">
          Light or Dark, or follow your device&apos;s setting. Saved in this browser.
        </p>
        <ThemeToggle initial={theme} />
      </Section>

      <Section title="Grading" id="grading-heading">
        <div className="mb-4 space-y-2 text-sm leading-relaxed text-muted-foreground">
          {ownKeyOnly ? (
            <p>
              Written answers are graded by an LLM against the Model Answer, with your own Google
              Gemini key.{" "}
              {me.is_admin
                ? "Every other Learner uses their own key, never yours."
                : "Save your key here before you answer written Questions: without one they can't be graded."}
            </p>
          ) : (
            <p>
              Written answers are graded by an LLM against the Model Answer. You can use your own
              free Google Gemini key.{" "}
              {me.is_admin
                ? "Learners without a key of their own are graded with yours."
                : "Without one, the Admin's key is used."}{" "}
              If a key&apos;s provider fails, the next one in line grades instead.
            </p>
          )}
          <ol className="list-decimal space-y-1 pl-5">
            <li>
              Sign in to{" "}
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noreferrer"
                className="font-medium text-primary underline underline-offset-4 hover:text-primary/80"
              >
                Google AI Studio
              </a>{" "}
              with your Google account and choose <strong>Create API key</strong>.
            </li>
            <li>Copy the key, paste it below and save it.</li>
          </ol>
          <p>
            Your key is stored encrypted, is only used to grade your answers
            {me.is_admin && !ownKeyOnly ? " (and those of Learners without a key)" : ""}, and is
            never shown again: only its last four characters.
          </p>
        </div>
        {grading && (
          <GradingKeyForm
            grading={grading}
            saveAction={saveGradingKey}
            removeAction={removeGradingKey}
          />
        )}
      </Section>

      <Section title="Claude connector (MCP)" id="mcp-heading">
        <div className="mb-4 space-y-2 text-sm leading-relaxed text-muted-foreground">
          <p>
            Connect Claude to the app to read the Syllabuses and propose new Questions and Daily
            Challenges. Everything it proposes is a draft, under your name, until the Admin accepts
            it.
          </p>
        </div>
        <AccessTokens
          mcpUrl={mcpUrl()}
          tokens={tokens ?? []}
          createAction={createAccessToken}
          revokeAction={revokeAccessToken}
        />
      </Section>
    </main>
  );
}
