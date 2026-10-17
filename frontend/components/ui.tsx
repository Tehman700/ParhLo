"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useSession } from "@/lib/auth";
import { LogoMark } from "./Logo";
import { NotificationBell } from "./NotificationBell";

const APP_LINKS = [
  { href: "/paper", label: "Today" },
  { href: "/archive", label: "Past papers" },
  { href: "/dashboard", label: "Dashboard" },
];

/** Global nav (apple-DESIGN.md → global-nav / sub-nav-frosted): 44px, frosted, 12px links. */
export function TopBar({ right }: { right?: ReactNode }) {
  const { ready, signedIn, isDemo, user, signOut } = useSession();
  const path = usePathname();
  const initial = (user?.name && user.name !== "Reader" ? user.name : user?.email ?? "?").charAt(0).toUpperCase();

  return (
    <header className="sticky top-0 z-40 border-b border-black/[0.06] bg-[#f5f5f7]/80 backdrop-blur-xl backdrop-saturate-[180%]">
      <div className="mx-auto flex h-11 max-w-[1024px] items-center gap-8 px-4 text-[12px] tracking-[-0.12px]">
        <Link href={signedIn ? "/paper" : "/"} aria-label="ParhLo home" className="flex items-center gap-1.5">
          <LogoMark size={20} />
          <span className="text-[14px] font-semibold tracking-tight text-ink">ParhLo</span>
        </Link>
        <nav className="hidden items-center gap-7 sm:flex">
          {signedIn ? APP_LINKS.map((l) => (
            <Link key={l.href} href={l.href}
              className={path?.startsWith(l.href) ? "text-ink" : "text-ink/80 transition-colors hover:text-ink"}>
              {l.label}
            </Link>
          )) : (
            <Link href="/how-it-works" className={path === "/how-it-works" ? "text-ink" : "text-ink/80 hover:text-ink"}>How it works</Link>
          )}
        </nav>
        <div className={`ml-auto flex items-center gap-4 transition-opacity ${ready ? "opacity-100" : "opacity-0"}`}>
          {right}
          {user ? (
            <>
              <NotificationBell />
              <Link href="/dashboard" className="flex items-center gap-2 text-ink/80 hover:text-ink" aria-label="Your dashboard">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-ink text-[11px] font-semibold text-white">{initial}</span>
                <span className="hidden max-w-[120px] truncate sm:inline">{user.name !== "Reader" ? user.name : user.email}</span>
              </Link>
              <button className="text-ink/80 hover:text-ink" onClick={() => signOut()}>Sign out</button>
            </>
          ) : isDemo ? (
            <>
              <span className="rounded-full bg-[#e8f1fb] px-2 py-0.5 font-semibold text-primary">Demo</span>
              <Link href="/sign-in" className="text-ink/80 hover:text-ink">Create an account</Link>
              <button className="text-ink/80 hover:text-ink" onClick={() => signOut()}>Exit demo</button>
            </>
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

/** Context-aware primary actions: signed-in readers go to their paper, demo readers can create an account. */
export function StartButtons({ center = true }: { center?: boolean }) {
  const { ready, user, isDemo } = useSession();
  const cls = `flex flex-wrap items-center gap-4 ${center ? "justify-center" : ""} ${ready ? "visible" : "invisible"}`;
  if (user) return (
    <div className={cls}>
      <Link href="/paper" className="btn btn-primary">Open my paper</Link>
      <Link href="/dashboard" className="btn btn-secondary">Dashboard</Link>
    </div>
  );
  if (isDemo) return (
    <div className={cls}>
      <Link href="/paper" className="btn btn-primary">Continue the demo</Link>
      <Link href="/sign-in" className="btn btn-secondary">Create a free account</Link>
    </div>
  );
  return (
    <div className={cls}>
      <Link href="/sign-in" className="btn btn-primary">Get started</Link>
      <Link href="/demo" className="btn btn-secondary">Try the demo</Link>
    </div>
  );
}

export function formatDate(iso: string, opts: Intl.DateTimeFormatOptions = { weekday: "long", day: "numeric", month: "long", year: "numeric" }) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", opts);
}
