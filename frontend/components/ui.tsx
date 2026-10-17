"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useSession } from "@/lib/auth";
import { LogoMark } from "./Logo";
import { ACCOUNT_LINKS, AccountMenu, HELP_LINKS, MobileMenu } from "./NavMenus";
import { NotificationBell } from "./NotificationBell";
import { SearchBox } from "./SearchBox";

const APP_LINKS = [
  { href: "/paper", label: "Today" },
  { href: "/archive", label: "Past papers" },
  { href: "/dashboard#saved", label: "Saved" },
  { href: "/dashboard", label: "Dashboard" },
];
const PUBLIC_LINKS = [
  { href: "/how-it-works", label: "How it works" },
  { href: "/jev", label: "How we check" },
  { href: "/about", label: "About" },
];

/** Global nav (apple-DESIGN.md → global-nav / sub-nav-frosted): 44px, frosted, 12px links.
 *  Main destinations in the bar; account, help and sign-out in the account menu; everything in a ☰ sheet on phones. */
export function TopBar({ right }: { right?: ReactNode }) {
  const { ready, signedIn, isDemo, user, signOut } = useSession();
  const path = usePathname();
  const initial = (user?.name && user.name !== "Reader" ? user.name : user?.email ?? "?").charAt(0).toUpperCase();
  const displayName = user ? (user.name !== "Reader" ? user.name : user.email ?? "Reader") : "";
  const links = signedIn ? APP_LINKS : PUBLIC_LINKS;
  const isActive = (href: string) => !href.includes("#") && (href === "/" ? path === "/" : path?.startsWith(href));

  return (
    <header className="sticky top-0 z-40 border-b border-black/[0.06] bg-[#f5f5f7]/80 backdrop-blur-xl backdrop-saturate-[180%]">
      <div className="mx-auto flex h-11 max-w-[1024px] items-center gap-8 px-4 text-[12px] tracking-[-0.12px]">
        <Link href={signedIn ? "/paper" : "/"} aria-label="ParhLo home" className="flex items-center gap-1.5">
          <LogoMark size={20} />
          <span className="text-[14px] font-semibold tracking-tight text-ink">ParhLo</span>
        </Link>
        <nav className="hidden items-center gap-7 sm:flex" aria-label="Main">
          {links.map((l) => (
            <Link key={l.href} href={l.href} aria-current={isActive(l.href) ? "page" : undefined}
              className={isActive(l.href) ? "text-ink" : "text-ink/80 transition-colors hover:text-ink"}>
              {l.label}
            </Link>
          ))}
        </nav>
        <div className={`ml-auto flex items-center gap-4 transition-opacity ${ready ? "opacity-100" : "opacity-0"}`}>
          {right}
          {(user || isDemo) && <SearchBox />}
          {user ? (
            <>
              <NotificationBell />
              <div className="hidden sm:block">
                <AccountMenu initial={initial} name={displayName} email={user.email} onSignOut={() => signOut()} />
              </div>
              <MobileMenu sections={[{ items: APP_LINKS }, { title: "Account", items: ACCOUNT_LINKS.filter((l) => l.href === "/dashboard#friends") }, { title: "Help", items: HELP_LINKS }]}
                footer={<button className="w-full rounded-full bg-ink py-2.5 text-[15px] text-white" onClick={() => signOut()}>Sign out</button>} />
            </>
          ) : isDemo ? (
            <>
              <span className="rounded-full bg-[#e8f1fb] px-2 py-0.5 font-semibold text-primary">Demo</span>
              <Link href="/sign-in" className="hidden text-ink/80 hover:text-ink sm:inline">Create an account</Link>
              <button className="hidden text-ink/80 hover:text-ink sm:inline" onClick={() => signOut()}>Exit demo</button>
              <MobileMenu sections={[{ items: APP_LINKS }, { title: "Help", items: HELP_LINKS }]}
                footer={<div className="flex gap-3">
                  <Link href="/sign-in" className="flex-1 rounded-full bg-primary py-2.5 text-center text-[15px] text-white">Create an account</Link>
                  <button className="flex-1 rounded-full bg-black/5 py-2.5 text-[15px] text-ink" onClick={() => signOut()}>Exit demo</button>
                </div>} />
            </>
          ) : (
            <>
              <Link href="/sign-in" className="hidden text-ink/80 hover:text-ink sm:inline">Sign in</Link>
              <Link href="/sign-in" className="btn btn-primary btn-sm !py-1 !text-[12px]">Get started</Link>
              <MobileMenu sections={[{ items: PUBLIC_LINKS }, { items: [{ href: "/demo", label: "Try the demo" }, { href: "/sign-in", label: "Sign in" }] }]} />
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
