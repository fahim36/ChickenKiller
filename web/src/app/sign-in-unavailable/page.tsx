import { CloudOff, RotateCw } from "lucide-react";
import Link from "next/link";
import { StatusScreen } from "@/components/StatusScreen";
import { Button } from "@/components/ui/button";

// Where the API's sign-in 503 lands (lib/api.ts): the API can't check sign-ins, because
// CLERK_ISSUER isn't set or Clerk's keys couldn't be fetched. It must not call the API itself.
export default function SignInUnavailablePage() {
  return (
    <StatusScreen
      icon={CloudOff}
      title="Sign-in can't be checked right now"
      action={
        <Button asChild size="lg" className="px-4">
          <Link href="/">
            <RotateCw aria-hidden />
            Try again
          </Link>
        </Button>
      }
      footnote={
        <>
          If it keeps happening, the Admin should check that the API has <code>CLERK_ISSUER</code>{" "}
          set and can reach Clerk (docs/deploy.md).
        </>
      }
    >
      The app couldn&apos;t check your sign-in. This is usually brief, so try again in a moment.
    </StatusScreen>
  );
}
