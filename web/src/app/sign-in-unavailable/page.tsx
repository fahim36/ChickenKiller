import Link from "next/link";

// Where the API's sign-in 503 lands (lib/api.ts): the API can't check sign-ins, because
// CLERK_ISSUER isn't set or Clerk's keys couldn't be fetched. It must not call the API itself.
export default function SignInUnavailablePage() {
  return (
    <main>
      <h1>Sign-in can&apos;t be checked right now</h1>
      <p>
        The app couldn&apos;t check your sign-in. This is usually brief, so try
        again in a moment.
      </p>
      <Link href="/">Try again</Link>
      <p className="muted">
        If it keeps happening, the Admin should check that the API has{" "}
        <code>CLERK_ISSUER</code> set and can reach Clerk (docs/deploy.md).
      </p>
    </main>
  );
}
