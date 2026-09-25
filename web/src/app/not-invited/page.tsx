import { SignOutButton } from "@clerk/nextjs";

// Where the API's "not invited" refusal lands (lib/api.ts). It must not call the API itself.
export default function NotInvitedPage() {
  return (
    <main>
      <h1>You haven&apos;t been invited yet</h1>
      <p>
        This app is invite-only, and the email address you signed in with isn&apos;t on the list.
        Ask the Admin for an invitation, then sign in again with that address.
      </p>
      <SignOutButton redirectUrl="/sign-in">
        <button type="button">Sign in with another account</button>
      </SignOutButton>
    </main>
  );
}
