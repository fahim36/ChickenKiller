import { SignIn } from "@clerk/nextjs";

// Email and Google are the sign-in methods enabled in the Clerk dashboard (docs/deploy.md).
export default function SignInPage() {
  return (
    <main className="centered">
      <SignIn />
    </main>
  );
}
