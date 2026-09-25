import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

// Next.js 16 calls middleware "proxy". Every page needs a signed-in person, except these.
const isPublic = createRouteMatcher(["/sign-in(.*)", "/sign-up(.*)", "/not-invited"]);

export default clerkMiddleware(
  async (auth, request) => {
    if (!isPublic(request)) await auth.protect();
  },
  { signInUrl: "/sign-in", signUpUrl: "/sign-up" },
);

export const config = {
  matcher: [
    // Skip Next.js internals and static files, unless found in search params.
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
