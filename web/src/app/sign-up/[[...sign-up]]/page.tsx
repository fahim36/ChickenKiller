import { SignUp } from "@clerk/nextjs";
import { AuthShell } from "@/components/AuthShell";

// A person creates their Clerk account here the first time. Anyone can create one. With the
// API's OPEN_SIGNUP on, everyone gets in; otherwise only invited email addresses do (see
// /not-invited).
export default function SignUpPage() {
  return (
    <AuthShell>
      <SignUp />
    </AuthShell>
  );
}
