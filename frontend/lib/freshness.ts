"use client";

import { useEffect, useRef, useState } from "react";
import type { Edition } from "./api";
import { useApi } from "./auth";

/** Fired by the dashboard after any change that affects which stories you get. */
export const INTERESTS_EVENT = "parhlo:interests-changed";
export const interestsChanged = () => window.dispatchEvent(new Event(INTERESTS_EVENT));

type Status = { stale: boolean; building: boolean; phase: string | null };
type Refresh = { status: "refreshed" | "skipped"; reason?: string; edition?: Edition };
/** updating: the fast reprint is running (≈1–2 s). polishing: AI summaries + editor run in the background. */
export type Freshness = "fresh" | "updating" | "polishing";
export type UpdateKind = "reprint" | "polish";

const DEBOUNCE_MS = 900;  // several quick toggles → one reprint

/**
 * Keeps today's paper in step with the reader's interests, without making them wait:
 * ~1 s after the last change it asks for a FAST reprint (no AI in the critical path) and swaps the new paper in
 * from that response, then asks for the AI polish and swaps that in silently. n8n does the same server-side
 * if the page is closed; whoever comes second finds the paper already up to date.
 */
export function usePaperFreshness(enabled: boolean, onUpdated: (edition: Edition, kind: UpdateKind) => void) {
  const api = useApi();
  const [state, setState] = useState<Freshness>("fresh");
  const busy = useRef(false);
  const dirty = useRef(false);
  const debounce = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const updated = useRef(onUpdated);
  const runRef = useRef<() => Promise<void>>(async () => {});
  useEffect(() => { updated.current = onUpdated; }, [onUpdated]);

  useEffect(() => {
    const polish = async () => {
      setState("polishing");
      try {
        const p = await api.post<{ edition: Edition | null }>("/api/editions/polish");
        if (p.edition && !busy.current) updated.current(p.edition, "polish");
      } catch { /* the fast paper stays; n8n or the next visit polishes it */ }
      if (!busy.current) setState("fresh");
    };

    const waitForBuild = async () => {  // someone else (n8n, another tab) is reprinting: wait for it
      for (let i = 0; i < 60; i++) {
        await new Promise((r) => setTimeout(r, 700));
        const s = await api.get<Status>("/api/editions/status").catch(() => null);
        if (s && !s.building) {
          updated.current(await api.post<Edition>("/api/editions/generate", {}), "reprint");
          return;
        }
      }
    };

    runRef.current = async () => {
      if (busy.current) { dirty.current = true; return; }
      busy.current = true;
      setState("updating");
      try {
        const r = await api.post<Refresh>("/api/editions/refresh");
        if (r.status === "refreshed" && r.edition) updated.current(r.edition, "reprint");
        else if (r.reason === "already reprinting") await waitForBuild();
      } catch { /* n8n will still reprint it */ }
      busy.current = false;
      if (dirty.current) { dirty.current = false; return runRef.current(); }
      await polish();
    };
  }, [api]);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    // On load: catch up if the paper is behind (changed in another tab, or n8n still on it), or unpolished.
    const start = setTimeout(async () => {
      const s = await api.get<Status>("/api/editions/status").catch(() => null);
      if (cancelled || !s) return;
      if (s.stale || s.building) void runRef.current();
      else if (s.phase === "fast") {
        setState("polishing");
        const p = await api.post<{ edition: Edition | null }>("/api/editions/polish").catch(() => null);
        if (!cancelled && p?.edition) updated.current(p.edition, "polish");
        if (!cancelled) setState("fresh");
      }
    }, 0);
    const onChange = () => {
      setState("updating");
      clearTimeout(debounce.current);
      debounce.current = setTimeout(() => void runRef.current(), DEBOUNCE_MS);
    };
    window.addEventListener(INTERESTS_EVENT, onChange);
    return () => {
      cancelled = true;
      clearTimeout(start);
      clearTimeout(debounce.current);
      window.removeEventListener(INTERESTS_EVENT, onChange);
    };
  }, [enabled, api]);

  return state;
}
