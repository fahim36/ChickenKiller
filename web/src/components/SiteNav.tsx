"use client";

import { House, Layers, Repeat, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Home", icon: House },
  { href: "/stacks", label: "Stacks", icon: Layers },
  { href: "/review", label: "Review", icon: Repeat },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

/** The signed-in navigation in the site header, with the current section highlighted. */
export function SiteNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="flex items-center gap-1">
      {LINKS.map(({ href, label, icon: Icon }) => {
        // A Stack's own pages (its Week map, Challenge, Archive) belong to Home; the Stacks
        // screen is only /stacks itself.
        const current =
          href === "/"
            ? pathname === "/" || pathname.startsWith("/stacks/") || pathname === "/catch-up"
            : href === "/stacks"
              ? pathname === "/stacks"
              : href === "/settings"
                ? pathname.startsWith("/settings") || pathname.startsWith("/admin")
                : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={current ? "page" : undefined}
            className={cn(
              "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
              current && "bg-muted text-foreground",
            )}
          >
            <Icon aria-hidden className="size-4" />
            <span className="hidden sm:inline">{label}</span>
            <span className="sr-only sm:hidden">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
