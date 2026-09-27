import { SignOutButton } from "@clerk/nextjs";

// Where the API's 401 lands (lib/api.ts): Clerk says the person is signed in, but the API
// couldn't verify their session token. It must not call the API itself.
export default function SignInFailedPage() {
  return (
    <main>
      <h1>Your sign-in couldn&apos;t be verified</h1>
      <p>
        You&apos;re signed in, but the app couldn&apos;t confirm who you are.
        Your sign-in may have expired. Sign out and sign in again.
      </p>
      <SignOutButton redirectUrl="/sign-in">
        <button type="button">Sign out and sign in again</button>
      </SignOutButton>
      <p className="muted">If this keeps happening, tell the Admin.</p>
    </main>
  );
}
