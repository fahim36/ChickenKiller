import { House, SearchX } from "lucide-react";
import Link from "next/link";
import { StatusScreen } from "@/components/StatusScreen";
import { Button } from "@/components/ui/button";

// Shown when a page calls notFound(): an unknown Stack, Lesson or Challenge, or an Admin page
// for someone who isn't the Admin. It renders inside the layout, so it must not call the API.
export default function NotFound() {
  return (
    <StatusScreen
      icon={SearchX}
      title="Page not found"
      action={
        <Button asChild size="lg" className="px-4">
          <Link href="/">
            <House aria-hidden />
            Back to your Stacks
          </Link>
        </Button>
      }
    >
      There&apos;s nothing here. The link may be old, or the page may have moved.
    </StatusScreen>
  );
}
