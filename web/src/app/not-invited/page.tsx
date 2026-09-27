import { SignOutButton } from "@clerk/nextjs";
import { MailQuestion } from "lucide-react";
import { StatusScreen } from "@/components/StatusScreen";
import { Button } from "@/components/ui/button";

// Where the API's "not invited" refusal lands (lib/api.ts). It must not call the API itself.
export default function NotInvitedPage() {
  return (
    <StatusScreen
      icon={MailQuestion}
      title="You haven't been invited yet"
      action={
        <SignOutButton redirectUrl="/sign-in">
          <Button type="button" size="lg" className="px-4">
            Sign in with another account
          </Button>
        </SignOutButton>
      }
    >
      This app is invite-only, and the email address you signed in with isn&apos;t on the list.
      Ask the Admin for an invitation, then sign in again with that address.
    </StatusScreen>
  );
}
