"use client";

import gsap from "gsap";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Notification } from "@/lib/api";
import { useApi } from "@/lib/auth";
import { formatDate } from "./ui";

function message(n: Notification): { text: string; href: string } {
  switch (n.kind) {
    case "invite_accepted": return { text: `${n.actor ?? "A friend"} accepted your invite. You're now friends.`, href: "/dashboard#friends" };
    case "friend_added": return { text: `You're now friends with ${n.actor ?? "your friend"}.`, href: "/dashboard#friends" };
    case "paper_ready": return { text: `Your paper for ${n.data.date ? formatDate(n.data.date, { weekday: "long", day: "numeric", month: "long" }) : "today"} is ready.${n.data.lead ? ` ${n.data.lead}` : ""}`, href: n.data.date ? `/paper/${n.data.date}` : "/paper" };
    case "paper_updated": return { text: "Today's paper was updated for your new interests.", href: "/paper" };
    default: return { text: "Something new in ParhLo.", href: "/dashboard" };
  }
}

function ago(iso: string) {
  const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (m < 1) return "now";
  if (m < 60) return `${m}m`;
  if (m < 1440) return `${Math.round(m / 60)}h`;
  return `${Math.round(m / 1440)}d`;
}

/** Bell with unread count; opening it marks everything read. Polls every minute. */
export function NotificationBell() {
  const api = useApi();
  const [data, setData] = useState<{ unread: number; items: Notification[] } | null>(null);
  const [open, setOpen] = useState(false);
  const panel = useRef<HTMLDivElement>(null);
  const wrap = useRef<HTMLDivElement>(null);

  const load = useCallback(() => api.get<{ unread: number; items: Notification[] }>("/api/notifications").then(setData).catch(() => {}), [api]);

  useEffect(() => {
    void load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, [load]);

  useEffect(() => {
    if (!open) return;
    gsap.fromTo(panel.current, { y: -8, opacity: 0 }, { y: 0, opacity: 1, duration: 0.25, ease: "power2.out" });
    const close = (e: MouseEvent) => { if (!wrap.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next && data?.unread) {
      await api.post("/api/notifications/read").catch(() => {});
      setData((d) => (d ? { unread: 0, items: d.items } : d));
    }
  }

  const unread = data?.unread ?? 0;
  return (
    <div ref={wrap} className="relative">
      <button aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"} onClick={toggle}
        className="relative flex h-7 w-7 items-center justify-center rounded-full text-ink/80 hover:text-ink">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
        </svg>
        {unread > 0 && (
          <span className="absolute -right-1 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      {open && (
        <div ref={panel} role="dialog" aria-label="Notifications"
          className="absolute right-0 top-9 w-[320px] max-w-[calc(100vw-32px)] overflow-hidden rounded-[18px] border border-hairline bg-canvas shadow-[0_12px_40px_-12px_rgba(0,0,0,.25)]">
          <p className="border-b border-divider px-4 py-3 t-caption font-semibold text-ink">Notifications</p>
          {!data?.items.length ? (
            <p className="px-4 py-6 t-caption text-ink-60">Nothing yet. We&apos;ll tell you when your paper is ready or a friend joins.</p>
          ) : (
            <ul className="max-h-[360px] overflow-y-auto">
              {data.items.map((n) => {
                const m = message(n);
                return (
                  <li key={n.id}>
                    <Link href={m.href} onClick={() => setOpen(false)} className={`flex gap-3 px-4 py-3 hover:bg-parchment ${n.read ? "" : "bg-[#f5f9fe]"}`}>
                      <span className={`mt-1.5 h-2 w-2 flex-none rounded-full ${n.read ? "bg-transparent" : "bg-primary"}`} />
                      <span className="flex-1 t-caption text-ink">{m.text}</span>
                      <span className="t-fine text-ink-48">{ago(n.created_at)}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
