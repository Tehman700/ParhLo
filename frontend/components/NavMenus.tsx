"use client";

import gsap from "gsap";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

export type NavItem = { href: string; label: string; external?: boolean };

/** Secondary destinations: live in the account menu (desktop) and the phone sheet, not the top bar. */
export const ACCOUNT_LINKS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard & settings" },
  { href: "/dashboard#saved", label: "Saved stories" },
  { href: "/dashboard#friends", label: "Invite friends" },
];
export const HELP_LINKS: NavItem[] = [
  { href: "/how-it-works", label: "How it works" },
  { href: "/jev", label: "How we check stories" },
  { href: "/help", label: "Help & contact" },
];

function useDismiss(open: boolean, close: () => void, box: React.RefObject<HTMLElement | null>) {
  const path = usePathname();
  useEffect(() => { close(); }, [path]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) close(); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open, close, box]);
}

function MenuLink({ item, onPick }: { item: NavItem; onPick: () => void }) {
  const cls = "block rounded-[8px] px-3 py-2 text-[14px] text-ink hover:bg-parchment focus:bg-parchment focus:outline-none";
  return item.external
    ? <a role="menuitem" href={item.href} className={cls} onClick={onPick}>{item.label}</a>
    : <Link role="menuitem" href={item.href} className={cls} onClick={onPick}>{item.label}</Link>;
}

/** Desktop: the avatar + name opens a small menu (account, help, sign out). */
export function AccountMenu({ initial, name, email, onSignOut }: { initial: string; name: string; email: string | null; onSignOut: () => void }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const close = () => setOpen(false);
  useDismiss(open, close, box);
  useEffect(() => {
    if (open && panel.current) {
      gsap.fromTo(panel.current, { opacity: 0, y: -6, scale: 0.98 }, { opacity: 1, y: 0, scale: 1, duration: 0.18, ease: "power2.out" });
      panel.current.querySelector<HTMLElement>("[role=menuitem]")?.focus();
    }
  }, [open]);
  return (
    <div ref={box} className="relative">
      <button data-tour="dashboard" aria-haspopup="menu" aria-expanded={open} aria-label="Account menu" onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 text-ink/80 hover:text-ink">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-ink text-[11px] font-semibold text-white">{initial}</span>
        <span className="max-w-[120px] truncate">{name}</span>
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden className={`transition-transform ${open ? "rotate-180" : ""}`}>
          <path d="M2 3.5 5 6.5 8 3.5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <div ref={panel} role="menu" className="absolute right-0 top-[calc(100%+10px)] w-[248px] origin-top-right rounded-[14px] border border-hairline bg-canvas p-1.5 shadow-[0_18px_48px_-16px_rgba(0,0,0,.28)]">
          <div className="px-3 pb-2 pt-1.5">
            <p className="truncate text-[14px] font-semibold text-ink">{name}</p>
            {email && <p className="truncate text-[12px] text-ink-48">{email}</p>}
          </div>
          <div className="border-t border-divider pt-1">{ACCOUNT_LINKS.map((l) => <MenuLink key={l.href} item={l} onPick={close} />)}</div>
          <div className="mt-1 border-t border-divider pt-1">{HELP_LINKS.map((l) => <MenuLink key={l.href} item={l} onPick={close} />)}</div>
          <div className="mt-1 border-t border-divider pt-1">
            <button role="menuitem" onClick={() => { close(); onSignOut(); }}
              className="block w-full rounded-[8px] px-3 py-2 text-left text-[14px] text-ink hover:bg-parchment focus:bg-parchment focus:outline-none">Sign out</button>
          </div>
        </div>
      )}
    </div>
  );
}

/** Phones: a ☰ button opens a sheet under the bar with every destination. */
export function MobileMenu({ sections, footer }: { sections: { title?: string; items: NavItem[] }[]; footer?: ReactNode }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const sheet = useRef<HTMLDivElement>(null);
  const path = usePathname();
  const close = () => setOpen(false);
  useDismiss(open, close, box);
  useEffect(() => {
    if (open && sheet.current) gsap.fromTo(sheet.current, { opacity: 0, y: -8 }, { opacity: 1, y: 0, duration: 0.22, ease: "power2.out" });
  }, [open]);
  return (
    <div ref={box} className="sm:hidden">
      <button aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open} onClick={() => setOpen((o) => !o)}
        className="-mr-1.5 flex h-8 w-8 items-center justify-center rounded-full text-ink hover:bg-black/5">
        <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
          {open ? <path d="M4 4l10 10M14 4 4 14" /> : <path d="M3 5h12M3 9h12M3 13h12" />}
        </svg>
      </button>
      {open && (
        <div ref={sheet} className="fixed inset-x-0 top-11 max-h-[calc(100vh-44px)] overflow-y-auto border-b border-hairline bg-[#f5f5f7] px-4 pb-6 pt-2 shadow-[0_24px_40px_-24px_rgba(0,0,0,.35)]">
          {sections.map((s, k) => (
            <div key={k} className={k ? "mt-3 border-t border-hairline pt-3" : ""}>
              {s.title && <p className="px-2 pb-1 text-[12px] font-semibold text-ink-48">{s.title}</p>}
              {s.items.map((l) => {
                const active = !l.external && !l.href.includes("#") && path?.startsWith(l.href);
                const cls = `block rounded-[10px] px-2 py-2.5 text-[17px] ${active ? "font-semibold text-ink" : "text-ink/85"} hover:bg-black/5`;
                return l.external
                  ? <a key={l.href} href={l.href} className={cls} onClick={close}>{l.label}</a>
                  : <Link key={l.href} href={l.href} className={cls} onClick={close}>{l.label}</Link>;
              })}
            </div>
          ))}
          {footer && <div className="mt-4 border-t border-hairline pt-4" onClick={close}>{footer}</div>}
        </div>
      )}
    </div>
  );
}
