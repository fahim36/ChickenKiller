import { SignUp } from "@clerk/nextjs";
import { AuthShell } from "@/components/AuthShell";

// An invited person creates their Clerk account here the first time. Anyone can create one, but
// only invited email addresses get past the API (see /not-invited).
export default function SignUpPage() {
  return (
    <AuthShell>
      <SignUp />
    </AuthShell>
  );
}
