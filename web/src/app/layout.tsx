import { ClerkProvider, Show, UserButton } from "@clerk/nextjs";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
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
  description: "Daily self-evaluation quizzes over an always-current study Syllabus.",
};

// The layout must not call the API: /not-invited renders inside it (lib/api.ts).
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <ClerkProvider signInUrl="/sign-in" signUpUrl="/sign-up">
          <header className="site">
            <Link href="/">Interview Cracker</Link>
            <Show when="signed-in">
              <nav className="site-nav">
                <Link href="/settings">Settings</Link>
                <UserButton />
              </nav>
            </Show>
          </header>
          {children}
        </ClerkProvider>
      </body>
    </html>
  );
}
