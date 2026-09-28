import { ClerkProvider, Show, UserButton } from "@clerk/nextjs";
import { Zap } from "lucide-react";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { cookies } from "next/headers";
import Link from "next/link";
import { SiteNav } from "@/components/SiteNav";
import { parseTheme, THEME_COOKIE } from "@/lib/theme";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Interview Cracker",
  description:
    "Daily self-evaluation quizzes over an always-current study Syllabus.",
};

// The layout must not call the API: /not-invited renders inside it (lib/api.ts). The theme comes
// from a cookie the Settings toggle sets, so the first paint already has it.
export default async function RootLayout({ children }: LayoutProps<"/">) {
  const theme = parseTheme((await cookies()).get(THEME_COOKIE)?.value);
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable}`}
      data-theme={theme === "system" ? undefined : theme}
    >
      <body>
        <ClerkProvider
          signInUrl="/sign-in"
          signUpUrl="/sign-up"
          appearance={{
            variables: {
              colorPrimary: "#4f46e5",
              borderRadius: "0.75rem",
              fontFamily: "inherit",
            },
          }}
        >
          <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur-md supports-backdrop-filter:bg-background/65">
            <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-4">
              <Link
                href="/"
                className="flex items-center gap-2 font-heading text-base font-semibold tracking-tight"
              >
                <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
                  <Zap aria-hidden className="size-4" />
                </span>
                Interview Cracker
              </Link>
              <Show when="signed-in">
                <div className="flex items-center gap-2">
                  <SiteNav />
                  <div className="flex size-7 items-center justify-center">
                    <UserButton />
                  </div>
                </div>
              </Show>
            </div>
          </header>
          <div className="mx-auto w-full max-w-7xl px-4 pt-8 pb-20 sm:pt-10">
            {children}
          </div>
        </ClerkProvider>
      </body>
    </html>
  );
}
