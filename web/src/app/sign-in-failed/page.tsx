import { SignOutButton } from "@clerk/nextjs";
import { ShieldAlert } from "lucide-react";
import { StatusScreen } from "@/components/StatusScreen";
import { Button } from "@/components/ui/button";

// Where the API's 401 lands (lib/api.ts): Clerk says the person is signed in, but the API
// couldn't verify their session token. It must not call the API itself.
export default function SignInFailedPage() {
  return (
    <StatusScreen
      icon={ShieldAlert}
      title="Your sign-in couldn't be verified"
      action={
        <SignOutButton redirectUrl="/sign-in">
          <Button type="button" size="lg" className="px-4">
            Sign out and sign in again
          </Button>
        </SignOutButton>
      }
      footnote="If this keeps happening, tell the Admin."
    >
      You&apos;re signed in, but the app couldn&apos;t confirm who you are. Your sign-in may have
      expired. Sign out and sign in again.
    </StatusScreen>
  );
}
