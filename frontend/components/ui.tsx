"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useSession } from "@/lib/auth";
import { LogoMark } from "./Logo";

const APP_LINKS = [
  { href: "/paper", label: "Today" },
  { href: "/archive", label: "Past papers" },
  { href: "/profile", label: "Interests" },
];

/** Global nav (apple-DESIGN.md → global-nav / sub-nav-frosted): 44px, frosted, 12px links. */
export function TopBar({ right }: { right?: ReactNode }) {
  const { signedIn, signOut, demoUser } = useSession();
  const router = useRouter();
  const path = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b border-black/[0.06] bg-[#f5f5f7]/80 backdrop-blur-xl backdrop-saturate-[180%]">
      <div className="mx-auto flex h-11 max-w-[1024px] items-center gap-8 px-4 text-[12px] tracking-[-0.12px]">
        <Link href={signedIn ? "/paper" : "/"} aria-label="ParhLo home" className="flex items-center gap-1.5">
          <LogoMark size={20} />
          <span className="text-[14px] font-semibold tracking-tight text-ink">ParhLo</span>
        </Link>
        {signedIn && (
          <nav className="hidden items-center gap-7 sm:flex">
            {APP_LINKS.map((l) => (
              <Link key={l.href} href={l.href}
                className={path?.startsWith(l.href) ? "text-ink" : "text-ink/80 transition-colors hover:text-ink"}>
                {l.label}
              </Link>
            ))}
          </nav>
        )}
        <div className="ml-auto flex items-center gap-4">
          {right}
          {signedIn ? (
            <button className="text-ink/80 hover:text-ink" onClick={() => signOut().then(() => router.push("/"))}>
              {demoUser ? "Exit demo" : "Sign out"}
            </button>
          ) : (
            <>
              <Link href="/sign-in" className="text-ink/80 hover:text-ink">Sign in</Link>
              <Link href="/sign-in" className="btn btn-primary btn-sm !py-1 !text-[12px]">Get started</Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

export function Spinner({ label, dark = false }: { label?: string; dark?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 caption ${dark ? "text-white/80" : "text-ink-60"}`} role="status">
      <span className="flex gap-1">
        <span className="dot h-1.5 w-1.5 rounded-full bg-current" />
        <span className="dot h-1.5 w-1.5 rounded-full bg-current" />
        <span className="dot h-1.5 w-1.5 rounded-full bg-current" />
      </span>
      {label}
    </span>
  );
}

export function ErrorNote({ error, onRetry }: { error: string | null | undefined; onRetry?: () => void }) {
  if (!error) return null;
  return (
    <div className="flex items-center justify-between gap-3 rounded-[12px] bg-[#fff2f2] px-4 py-3 caption text-danger" role="alert">
      <span>{error}</span>
      {onRetry && <button className="font-semibold" onClick={onRetry}>Try again</button>}
    </div>
  );
}

export function formatDate(iso: string, opts: Intl.DateTimeFormatOptions = { weekday: "long", day: "numeric", month: "long", year: "numeric" }) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", opts);
}
