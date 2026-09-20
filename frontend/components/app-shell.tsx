"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/scholarships", label: "Scholarships" },
  { href: "/applications", label: "Pipeline" },
  { href: "/notifications", label: "Notifications" },
  { href: "/profile", label: "Profile" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-border/70 bg-[hsla(210,40%,98%,0.85)] backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <Link href="/dashboard" className="font-display text-xl tracking-tight text-primary">
            Scholarship Autopilot
          </Link>
          <nav className="hidden items-center gap-1 md:flex">
            {links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={cn(
                  "rounded-md px-3 py-2 text-sm transition",
                  pathname.startsWith(l.href)
                    ? "bg-secondary text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {l.label}
              </Link>
            ))}
          </nav>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              authApi.logout();
              router.push("/login");
            }}
          >
            Sign out
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 animate-fade-up">{children}</main>
    </div>
  );
}
