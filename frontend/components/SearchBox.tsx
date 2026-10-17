"use client";

import gsap from "gsap";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";
import type { Me } from "@/lib/api";
import { useApi } from "@/lib/auth";
import { interestsChanged } from "@/lib/freshness";
import { timeAgo } from "@/lib/topics";

type Hit = {
  id: number; title: string; source: string; url: string; image: string | null; published_at: string | null;
  topic: string | null; summary: string; in_paper: boolean; paper_story_id: number | null; saved: boolean;
};
type Result = { query: string; results: Hit[]; can_follow: boolean; ms: number };

const RECENT_KEY = "parhlo.recentSearches";
const readRecent = (): string[] => { try { return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]"); } catch { return []; } };
const saveRecent = (q: string) => {
  try { localStorage.setItem(RECENT_KEY, JSON.stringify([q, ...readRecent().filter((x) => x.toLowerCase() !== q.toLowerCase())].slice(0, 6))); } catch {}
};

function Icon({ d, size = 15 }: { d: string; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d={d} /></svg>;
}
const SEARCH = "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM21 21l-4.3-4.3";

/** Search the news from the top bar: by meaning and by words, your paper first, open the original on click. */
export function SearchBox() {
  const api = useApi();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [days, setDays] = useState(2);
  const [region, setRegion] = useState<"" | "pakistan" | "global">("");
  const [res, setRes] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [active, setActive] = useState(0);
  const [recent, setRecent] = useState<string[]>([]);
  const [following, setFollowing] = useState<string[]>([]);
  const [followNote, setFollowNote] = useState<string | null>(null);
  const [saved, setSaved] = useState<Record<number, boolean>>({});
  const seq = useRef(0);
  const panel = useRef<HTMLDivElement>(null);
  const field = useRef<HTMLInputElement>(null);

  const show = useCallback(() => {
    setRecent(readRecent());
    setOpen(true);
    api.get<Me>("/api/me").then((m) => setFollowing(m.profile?.entities ?? [])).catch(() => {});
  }, [api]);

  // "/" or Ctrl/⌘+K opens search from anywhere
  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      const typing = /input|textarea|select/i.test((e.target as HTMLElement)?.tagName) || (e.target as HTMLElement)?.isContentEditable;
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !typing)) { e.preventDefault(); show(); }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [show]);

  useEffect(() => {
    if (!open) return;
    document.body.style.overflow = "hidden";
    gsap.fromTo(panel.current, { opacity: 0, y: -12, scale: 0.98 }, { opacity: 1, y: 0, scale: 1, duration: 0.25, ease: "power3.out" });
    setTimeout(() => field.current?.focus(), 50);
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  // search as you type (debounced); late answers to older queries are ignored
  useEffect(() => {
    if (!open) return;
    const query = q.trim();
    if (query.length < 2) return;  // the panel shows recent searches instead
    const id = ++seq.current;
    const t = setTimeout(async () => {
      setBusy(true);
      try {
        const r = await api.get<Result>(`/api/search?q=${encodeURIComponent(query)}&days=${days}${region ? `&region=${region}` : ""}`);
        if (id === seq.current) { setRes(r); setActive(0); setFollowNote(null); }
      } catch { if (id === seq.current) setRes({ query, results: [], can_follow: false, ms: 0 }); }
      finally { if (id === seq.current) setBusy(false); }
    }, 300);
    return () => clearTimeout(t);
  }, [q, days, region, open, api]);

  const hits = res?.results ?? [];
  const mine = hits.filter((h) => h.in_paper);
  const more = hits.filter((h) => !h.in_paper);
  const ordered = [...mine, ...more];

  function openHit(h: Hit) {
    saveRecent(q.trim());
    api.post("/api/events", [{ type: "open", article_id: h.id }]).catch(() => {});  // reading signal
    window.open(h.url, "_blank", "noopener,noreferrer");
  }

  async function toggleSave(h: Hit) {
    const now = !(saved[h.id] ?? h.saved);
    setSaved((s) => ({ ...s, [h.id]: now }));
    await api.post("/api/events", [{ type: now ? "save" : "unsave", article_id: h.id }]).catch(() => {});
  }

  async function follow() {
    const name = res?.query;
    if (!name) return;
    try {
      await api.post("/api/me/following", { name });
      setFollowNote(`Following “${name}”. Your paper is updating.`);
      setFollowing((f) => [...f, name]);
      setRes((r) => (r ? { ...r, can_follow: false } : r));
      saveRecent(name);
      interestsChanged();
    } catch (e) {
      setFollowNote((e as Error).message);
    }
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, ordered.length - 1)); }
    if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
    if (e.key === "Enter" && ordered[active]) { e.preventDefault(); openHit(ordered[active]); }
  }

  const row = (h: Hit) => {
    const i = ordered.indexOf(h);
    const isSaved = saved[h.id] ?? h.saved;
    return (
      <li key={h.id} onMouseEnter={() => setActive(i)}
        className={`group flex gap-3 rounded-[14px] px-3 py-3 ${i === active ? "bg-parchment" : ""}`}>
        <button className="min-w-0 flex-1 text-left" onClick={() => openHit(h)} aria-label={`${h.title} — open on ${h.source}`}>
          <p className="t-fine font-semibold text-primary">{h.topic ?? "News"}</p>
          <p className="mt-0.5 text-[15px] font-semibold leading-snug text-ink">{h.title}</p>
          {h.summary && <p className="mt-1 line-clamp-2 t-caption text-ink-60">{h.summary}</p>}
          <p className="mt-1 t-fine text-ink-48">{h.source}{h.published_at ? ` · ${timeAgo(h.published_at)}` : ""} · opens the original ↗</p>
        </button>
        <div className="flex flex-none flex-col items-end gap-1.5 pt-0.5">
          <button onClick={() => toggleSave(h)} aria-label={isSaved ? "Remove from saved" : "Save"} title={isSaved ? "Saved" : "Save"}
            className={`flex h-8 w-8 items-center justify-center rounded-full hover:bg-black/5 ${isSaved ? "text-primary" : "text-ink-48"}`}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill={isSaved ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.8"><path d="M6 3h12v18l-6-4-6 4V3Z" /></svg>
          </button>
          {h.in_paper && h.paper_story_id && (
            <button onClick={() => { setOpen(false); router.push(`/paper?ask=${h.paper_story_id}#story-${h.paper_story_id}`); }}
              className="rounded-full bg-[#e8f1fb] px-2.5 py-1 t-fine font-semibold text-primary hover:bg-[#d6e6f8]">Ask</button>
          )}
        </div>
      </li>
    );
  };

  const chip = (on: boolean, label: string, onClick: () => void) => (
    <button onClick={onClick} className={`rounded-full px-3 py-1 t-fine font-medium ${on ? "bg-ink text-white" : "bg-parchment text-ink-80 hover:bg-black/10"}`}>{label}</button>
  );

  return (
    <>
      <button onClick={show} aria-label="Search the news" title="Search ( / )"
        className="flex items-center gap-1.5 rounded-full text-ink/80 hover:text-ink sm:bg-black/[0.05] sm:px-3 sm:py-1">
        <Icon d={SEARCH} size={14} /><span className="hidden lg:inline">Search</span>
      </button>
      {open && typeof document !== "undefined" && createPortal(
        <div className="fixed inset-0 z-[60] flex items-start justify-center bg-black/30 backdrop-blur-sm sm:pt-[10vh]" onMouseDown={(e) => { if (e.target === e.currentTarget) setOpen(false); }}>
          <div ref={panel} role="dialog" aria-label="Search the news"
            className="flex h-full w-full flex-col overflow-hidden bg-canvas sm:h-auto sm:max-h-[75vh] sm:max-w-[640px] sm:rounded-[22px] sm:shadow-[0_24px_64px_-16px_rgba(0,0,0,.35)]">
            <div className="flex items-center gap-3 border-b border-divider px-5 py-4">
              <span className="text-ink-48"><Icon d={SEARCH} size={18} /></span>
              <input ref={field} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={onKey} maxLength={120}
                placeholder="Search the news: people, places, topics…" aria-label="Search the news"
                className="flex-1 bg-transparent text-[17px] outline-none placeholder:text-ink-48" />
              {busy && <span className="flex gap-1"><span className="dot h-1.5 w-1.5 rounded-full bg-primary" /><span className="dot h-1.5 w-1.5 rounded-full bg-primary" /><span className="dot h-1.5 w-1.5 rounded-full bg-primary" /></span>}
              <button onClick={() => setOpen(false)} className="rounded-full bg-parchment px-2.5 py-1 t-fine text-ink-60 hover:text-ink">Esc</button>
            </div>
            <div className="flex flex-wrap gap-1.5 border-b border-divider px-5 py-2.5">
              {chip(days === 2, "Last 2 days", () => setDays(2))}
              {chip(days === 7, "This week", () => setDays(7))}
              <span className="mx-1 w-px bg-divider" />
              {chip(region === "", "All", () => setRegion(""))}
              {chip(region === "pakistan", "Pakistan", () => setRegion("pakistan"))}
              {chip(region === "global", "World", () => setRegion("global"))}
            </div>

            <div className="flex-1 overflow-y-auto px-2 py-2" data-query={res?.query ?? ""}>
              {q.trim().length < 2 ? (
                <div className="px-3 py-3">
                  {recent.length > 0 && (
                    <>
                      <p className="t-fine font-semibold text-ink-48">Recent</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">{recent.map((r) => <button key={r} onClick={() => setQ(r)} className="rounded-full border border-hairline px-3 py-1 t-caption hover:border-primary hover:text-primary">{r}</button>)}</div>
                    </>
                  )}
                  {following.length > 0 && (
                    <>
                      <p className="mt-4 t-fine font-semibold text-ink-48">You follow</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">{following.map((r) => <button key={r} onClick={() => setQ(r)} className="rounded-full bg-[#e8f1fb] px-3 py-1 t-caption text-primary hover:bg-[#d6e6f8]">{r}</button>)}</div>
                    </>
                  )}
                  <p className="mt-4 t-caption text-ink-60">Search finds stories by meaning, not just exact words: try “fuel prices” or “AI rules”. Results from your paper come first; clicking a story opens the original article.</p>
                </div>
              ) : res && hits.length === 0 && !busy ? (
                <p className="px-3 py-6 text-center t-body text-ink-60">No stories about “{res.query}” in the {days === 2 ? "last 2 days" : "last week"}.{days === 2 && <> <button className="link" onClick={() => setDays(7)}>Search this week</button></>}</p>
              ) : (
                <>
                  {res?.can_follow && (
                    <div className="mx-3 mb-2 mt-1 flex items-center justify-between gap-3 rounded-[14px] bg-[#e8f1fb] px-4 py-3">
                      <p className="t-caption text-ink">Want more about <strong>{res.query}</strong> in your paper?</p>
                      <button onClick={follow} className="btn btn-primary btn-sm !py-1.5 !text-[13px]">Follow “{res.query}”</button>
                    </div>
                  )}
                  {followNote && <p className="mx-3 mb-2 rounded-[14px] bg-[#eaf6ec] px-4 py-2.5 t-caption text-success" role="status">✓ {followNote}</p>}
                  {mine.length > 0 && (<><p className="px-3 pt-2 t-fine font-semibold text-ink-48">In your paper</p><ul>{mine.map(row)}</ul></>)}
                  {more.length > 0 && (<><p className="px-3 pt-3 t-fine font-semibold text-ink-48">More news</p><ul>{more.map(row)}</ul></>)}
                </>
              )}
            </div>
            <div className="hidden items-center justify-between border-t border-divider px-5 py-2.5 t-fine text-ink-48 sm:flex">
              <span>↑ ↓ to move · Enter to open · Esc to close</span>
              {res && hits.length > 0 && <span>{hits.length} stories · {res.ms} ms</span>}
            </div>
          </div>
        </div>, document.body)}
    </>
  );
}
