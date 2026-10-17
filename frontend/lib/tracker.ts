"use client";

import { useCallback, useEffect, useRef } from "react";
import { API_URL, type EventType } from "./api";
import { useSession } from "./auth";

type Ev = { type: EventType; article_id?: number; edition_id?: number; value?: number };

/** Batches reading signals (the paper's short-term memory) and measures dwell time per story. */
export function useTracker(editionId: number | undefined) {
  const { headers } = useSession();
  const queue = useRef<Ev[]>([]);
  const visibleSince = useRef(new Map<number, number>());
  const dwell = useRef(new Map<number, number>());
  const reported = useRef(new Set<number>());

  const flush = useCallback(async () => {
    // Report dwell once per story, when it crossed ~8s of visible reading.
    for (const [id, ms] of dwell.current) {
      if (ms >= 8000 && !reported.current.has(id)) {
        reported.current.add(id);
        queue.current.push({ type: "dwell", article_id: id, edition_id: editionId, value: Math.round(ms / 1000) });
      }
    }
    if (!queue.current.length) return;
    const batch = queue.current.splice(0);
    try {
      await fetch(`${API_URL}/api/events`, {
        method: "POST", keepalive: true,
        headers: { "Content-Type": "application/json", ...(await headers()) },
        body: JSON.stringify(batch),
      });
    } catch {
      queue.current.unshift(...batch);
    }
  }, [editionId, headers]);

  const track = useCallback((type: EventType, articleId?: number, value?: number) => {
    queue.current.push({ type, article_id: articleId, edition_id: editionId, value });
    if (type !== "dwell") void flush();
  }, [editionId, flush]);

  const observe = useCallback((el: HTMLElement | null, articleId: number) => {
    if (!el) return;
    const io = new IntersectionObserver(([entry]) => {
      const now = performance.now();
      if (entry.isIntersecting) visibleSince.current.set(articleId, now);
      else {
        const since = visibleSince.current.get(articleId);
        if (since) dwell.current.set(articleId, (dwell.current.get(articleId) ?? 0) + now - since);
        visibleSince.current.delete(articleId);
      }
    }, { threshold: 0.6 });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    const tick = setInterval(() => {
      const now = performance.now();
      for (const [id, since] of visibleSince.current) {
        dwell.current.set(id, (dwell.current.get(id) ?? 0) + now - since);
        visibleSince.current.set(id, now);
      }
      void flush();
    }, 10000);
    const onHide = () => void flush();
    window.addEventListener("pagehide", onHide);
    return () => { clearInterval(tick); window.removeEventListener("pagehide", onHide); void flush(); };
  }, [flush]);

  return { track, observe };
}
