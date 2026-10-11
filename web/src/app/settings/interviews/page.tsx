import { connection } from "next/server";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import {
  InterviewSettingsForm,
  type InterviewSettings,
} from "./InterviewSettingsForm";

export default async function InterviewSettingsPage() {
  await connection();
  const settings = await api<InterviewSettings>("/me/interview-settings");
  return (
    <main className="mx-auto max-w-3xl">
      <PageHeader title="Interview AI settings" />
      {settings ? (
        <InterviewSettingsForm initial={settings} />
      ) : (
        <p>Settings could not be loaded. Reload to try again.</p>
      )}
    </main>
  );
}
