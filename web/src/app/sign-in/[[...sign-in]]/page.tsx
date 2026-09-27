import { SignIn } from "@clerk/nextjs";
import { AuthShell } from "@/components/AuthShell";

// Email and Google are the sign-in methods enabled in the Clerk dashboard (docs/deploy.md).
export default function SignInPage() {
  return (
    <AuthShell>
      <SignIn />
    </AuthShell>
  );
}
