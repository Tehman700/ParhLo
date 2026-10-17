"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useSession } from "@/lib/auth";
import { Logo } from "./Logo";

export function TopBar({ right }: { right?: ReactNode }) {
  const { signedIn, signOut, demoUser } = useSession();
  const router = useRouter();
  return (
    <header className="sticky top-0 z-40 border-b border-hairline bg-parchment/80 backdrop-blur-xl backdrop-saturate-150">
      <div className="mx-auto flex h-14 max-w-[1200px] items-center gap-6 px-4 sm:px-6">
        <Link href={signedIn ? "/paper" : "/"} aria-label="ParhLo home"><Logo size={30} /></Link>
        {signedIn && (
          <nav className="hidden items-center gap-5 text-[14px] text-ink-80 sm:flex">
            <Link href="/paper" className="hover:text-ink">Today</Link>
            <Link href="/archive" className="hover:text-ink">Archive</Link>
            <Link href="/profile" className="hover:text-ink">Your memory</Link>
          </nav>
        )}
        <div className="ml-auto flex items-center gap-2">
          {right}
          {signedIn ? (
            <button className="btn btn-light !px-4 !py-2 !text-[14px]" onClick={() => signOut().then(() => router.push("/"))}>
              {demoUser ? "Exit demo" : "Sign out"}
            </button>
          ) : (
            <>
              <Link href="/sign-in" className="btn btn-ghost !text-[14px]">Sign in</Link>
              <Link href="/sign-in" className="btn btn-primary !px-4 !py-2 !text-[14px]">Get my paper</Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

export function Spinner({ label, dark = false }: { label?: string; dark?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 caption ${dark ? "text-white/70" : "text-ink-48"}`} role="status">
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
    <div className="flex items-center justify-between gap-3 rounded-[11px] bg-[#fff1f0] px-4 py-3 caption text-danger" role="alert">
      <span>{error}</span>
      {onRetry && <button className="font-semibold underline" onClick={onRetry}>Try again</button>}
    </div>
  );
}

export function formatDate(iso: string, opts: Intl.DateTimeFormatOptions = { weekday: "long", day: "numeric", month: "long", year: "numeric" }) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", opts);
}
