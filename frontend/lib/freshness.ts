"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useApi } from "./auth";

/** Fired by the dashboard after any change that affects which stories you get. */
export const INTERESTS_EVENT = "parhlo:interests-changed";
export const interestsChanged = () => window.dispatchEvent(new Event(INTERESTS_EVENT));

type Status = { stale: boolean; building: boolean; printed_at: string | null; interests_changed_at: string | null; orchestrator: string | null };
export type Freshness = "fresh" | "pending" | "building";

/** If n8n hasn't started the reprint this long after the change, ask for it ourselves. */
const FALLBACK_AFTER_MS = 25_000;
const POLL_MS = 3_000;

/**
 * Watches whether today's paper is out of date with the reader's interests.
 * n8n normally reprints it (debounced); this hook shows progress, calls onUpdated when the new print lands,
 * and falls back to asking for the reprint directly if the n8n event never arrived.
 */
export function usePaperFreshness(enabled: boolean, onUpdated: () => void) {
  const api = useApi();
  const [state, setState] = useState<Freshness>("fresh");
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const printed = useRef<string | null | undefined>(undefined);
  const staleSince = useRef<number | null>(null);
  const askedFallback = useRef(false);
  const updated = useRef(onUpdated);
  const next = useRef<() => void>(() => {});  // the poll scheduling itself again
  useEffect(() => { updated.current = onUpdated; }, [onUpdated]);

  const poll = useCallback(async () => {
    clearTimeout(timer.current);
    let s: Status;
    try {
      s = await api.get<Status>("/api/editions/status");
    } catch {
      timer.current = setTimeout(() => next.current(), POLL_MS * 2);
      return;
    }
    if (printed.current === undefined) printed.current = s.printed_at;
    if (s.building) {
      setState("building");
    } else if (s.stale) {
      setState("pending");
      staleSince.current ??= s.interests_changed_at ? Date.parse(s.interests_changed_at) : Date.now();
      if (!askedFallback.current && Date.now() - staleSince.current > FALLBACK_AFTER_MS) {
        askedFallback.current = true;
        api.post("/api/editions/refresh").catch(() => {});
      }
    } else {
      if (printed.current && s.printed_at && s.printed_at !== printed.current) updated.current();
      printed.current = s.printed_at;
      staleSince.current = null;
      askedFallback.current = false;
      setState("fresh");
      return;
    }
    timer.current = setTimeout(() => next.current(), POLL_MS);
  }, [api]);
  useEffect(() => { next.current = () => void poll(); }, [poll]);

  useEffect(() => {
    if (!enabled) return;
    timer.current = setTimeout(() => next.current(), 0);
    const onChange = () => {
      staleSince.current = Date.now();
      askedFallback.current = false;
      setState("pending");
      clearTimeout(timer.current);
      timer.current = setTimeout(() => next.current(), 1200);
    };
    window.addEventListener(INTERESTS_EVENT, onChange);
    return () => {
      window.removeEventListener(INTERESTS_EVENT, onChange);
      clearTimeout(timer.current);
    };
  }, [enabled]);

  return state;
}
