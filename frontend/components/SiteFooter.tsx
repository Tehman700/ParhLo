"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const COLUMNS = [
  { title: "ParhLo", links: [["How it works", "/how-it-works"], ["Try the demo", "/demo"], ["Sign in", "/sign-in"]] },
  { title: "Your account", links: [["Today's paper", "/paper"], ["Past papers", "/archive"], ["Dashboard", "/dashboard"]] },
  { title: "About", links: [["About ParhLo", "/about"], ["Privacy Policy", "/privacy"], ["Terms of Use", "/terms"]] },
] as const;

const HIDDEN = ["/onboarding", "/sign-in", "/sign-up", "/sso-callback"];

/** Site-wide footer (apple-DESIGN.md → footer): parchment, dense link columns, fine print. */
export function SiteFooter() {
  const path = usePathname() ?? "/";
  if (HIDDEN.some((p) => path.startsWith(p)) || path.endsWith("/print")) return null;
  return (
    <footer className="border-t border-hairline bg-parchment px-4 pb-8 pt-10">
      <div className="mx-auto max-w-[980px]">
        <p className="t-fine text-ink-48">
          Summaries in ParhLo are written by AI from the linked articles and checked against them. They can still contain
          mistakes, so every story links to the original.
        </p>
        <div className="mt-6 grid gap-8 border-t border-hairline pt-6 sm:grid-cols-3">
          {COLUMNS.map((c) => (
            <div key={c.title}>
              <p className="t-fine font-semibold text-ink">{c.title}</p>
              <ul className="mt-2 space-y-1.5">
                {c.links.map(([label, href]) => (
                  <li key={href}><Link href={href} className="t-fine text-ink-60 hover:text-ink hover:underline">{label}</Link></li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-8 flex flex-col gap-2 border-t border-hairline pt-4 t-fine text-ink-48 sm:flex-row sm:justify-between">
          <span>Copyright © 2026 ParhLo. All rights reserved.</span>
          <span className="flex gap-4">
            <Link href="/privacy" className="hover:text-ink">Privacy Policy</Link>
            <Link href="/terms" className="hover:text-ink">Terms of Use</Link>
            <a href="mailto:tehmanhassan@gmail.com" className="hover:text-ink">Contact</a>
          </span>
        </div>
      </div>
    </footer>
  );
}
