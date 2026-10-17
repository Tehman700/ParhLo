"use client";

import gsap from "gsap";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Me } from "@/lib/api";
import { useApi, useSession } from "@/lib/auth";

const DONE_KEY = "parhlo.tour.v1";
const NEW_FOR_MS = 3 * 24 * 3600_000; // accounts younger than this count as new readers

type Step = { target?: string; title: string; body: string };

const STEPS: Step[] = [
  { title: "Welcome to your first paper", body: "This is ParhLo: one short paper, made for you every morning. Here's a quick tour of what you can do. It takes about 30 seconds." },
  { target: "[data-tour='lead']", title: "Your top story", body: "The story that matters most to you today. Click a headline to read the full article on the original site." },
  { target: "[data-tour='checked']", title: "Checked against the source", body: "Every summary is checked against the original article. Hover this badge to see how." },
  { target: "[data-tour='actions']", title: "Teach your paper", body: "More like this, less like this, save for later, or hide. Every click changes tomorrow's paper." },
  { target: "[data-tour='three']", title: "Three things to remember", body: "The key points from today. Tomorrow's paper starts with a short quiz on them." },
  { target: "[data-tour='ask']", title: "Ask your paper", body: "Ask anything about today's stories. Answers come only from your paper, with sources." },
  { target: "[data-tour='pdf']", title: "Download the PDF", body: "The same paper as a newspaper you can save, print or read offline." },
  { target: "[data-tour='dashboard']", title: "Your dashboard", body: "Change topics and reading time, and see everything ParhLo has learned about you." },
  { title: "You're all set", body: "Read, react, and come back tomorrow. Your paper gets better every day." },
];

const markDone = () => { try { localStorage.setItem(DONE_KEY, "1"); } catch {} };

/** First-paper walkthrough. Only for new readers (account under 3 days old, not a sample reader) who haven't
 *  finished or skipped it on this device. A spotlight follows each feature; the card explains it. */
export function Tour() {
  const api = useApi();
  const { ready, signedIn } = useSession();
  const [active, setActive] = useState(false);
  const [i, setI] = useState(0);
  const spot = useRef<HTMLDivElement>(null);
  const card = useRef<HTMLDivElement>(null);
  const cur = useRef({ x: 0, y: 0, w: 0, h: 0, init: false });

  // Decide once whether this reader should see the tour.
  useEffect(() => {
    if (!ready || !signedIn) return;
    try { if (localStorage.getItem(DONE_KEY)) return; } catch { return; }
    let cancelled = false;
    api.get<Me>("/api/me").then((me) => {
      const fresh = Date.now() - new Date(me.user.created_at).getTime() < NEW_FOR_MS;
      if (cancelled) return;
      if (fresh && me.user.onboarded && !me.user.persona) window.setTimeout(() => !cancelled && setActive(true), 1400); // let the paper settle in
      else markDone(); // a returning reader: never show it on this device
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [ready, signedIn, api]);

  const steps = STEPS.filter((s) => !s.target || typeof document === "undefined" || document.querySelector(s.target));
  const step = steps[Math.min(i, steps.length - 1)];

  const close = useCallback(() => { markDone(); setActive(false); }, []);
  const next = useCallback(() => (i >= steps.length - 1 ? close() : setI(i + 1)), [i, steps.length, close]);
  const back = useCallback(() => setI(Math.max(0, i - 1)), [i]);

  // Keyboard: → / Enter next, ← back, Esc skip.
  useEffect(() => {
    if (!active) return;
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      else if (e.key === "ArrowRight" || e.key === "Enter") { e.preventDefault(); next(); }
      else if (e.key === "ArrowLeft") back();
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [active, next, back, close]);

  // Bring the step's feature into view, then animate the card in.
  useEffect(() => {
    if (!active) return;
    const el = step?.target ? document.querySelector<HTMLElement>(step.target) : null;
    if (el && getComputedStyle(el).position !== "fixed") el.scrollIntoView({ behavior: "smooth", block: "center" });
    if (card.current) gsap.fromTo(card.current, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.35, ease: "power3.out", delay: 0.15 });
  }, [active, step]);

  // Spotlight + card follow the target every frame (handles smooth scrolling, sticky bars and resizes).
  useEffect(() => {
    if (!active) return;
    let raf = 0;
    const loop = () => {
      const el = step?.target ? document.querySelector<HTMLElement>(step.target) : null;
      const pad = 8, vw = window.innerWidth, vh = window.innerHeight;
      const r = el?.getBoundingClientRect();
      const t = r ? { x: r.left - pad, y: r.top - pad, w: r.width + pad * 2, h: r.height + pad * 2 } : { x: vw / 2, y: vh / 2, w: 0, h: 0 };
      const c = cur.current;
      if (!c.init) Object.assign(c, t, { init: true });
      c.x += (t.x - c.x) * 0.22; c.y += (t.y - c.y) * 0.22; c.w += (t.w - c.w) * 0.22; c.h += (t.h - c.h) * 0.22;
      if (spot.current) Object.assign(spot.current.style, { left: `${c.x}px`, top: `${c.y}px`, width: `${c.w}px`, height: `${c.h}px` });
      if (card.current) {
        const cw = card.current.offsetWidth, ch = card.current.offsetHeight;
        let left: number, top: number;
        if (!r) { left = (vw - cw) / 2; top = (vh - ch) / 2; }
        else {
          const below = r.bottom + pad + 14 + ch < vh - 12;
          top = below ? r.bottom + pad + 14 : Math.max(12, r.top - pad - 14 - ch);
          left = Math.min(Math.max(12, r.left + r.width / 2 - cw / 2), vw - cw - 12);
        }
        card.current.style.left = `${left}px`; card.current.style.top = `${top}px`;
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [active, step]);

  if (!active || !step) return null;
  const last = i >= steps.length - 1;

  return (
    <div className="fixed inset-0 z-[90]" role="dialog" aria-modal="true" aria-label="ParhLo tour">
      {/* Dim everything except the spotlight (one huge shadow around a rounded window). */}
      <div ref={spot} className="pointer-events-none fixed rounded-[16px] shadow-[0_0_0_9999px_rgba(0,0,0,0.55)] ring-2 ring-white/80" />
      <div className="absolute inset-0" onClick={(e) => e.stopPropagation()} />
      <div ref={card} className="fixed w-[min(360px,calc(100vw-24px))] rounded-[18px] bg-canvas p-5 shadow-[0_24px_64px_-16px_rgba(0,0,0,.45)]">
        <p className="t-fine font-semibold text-primary">Step {i + 1} of {steps.length}</p>
        <h2 className="mt-1 text-[19px] font-semibold leading-tight">{step.title}</h2>
        <p className="mt-2 t-caption text-ink-60">{step.body}</p>
        <div className="mt-4 flex items-center gap-1.5" aria-hidden>
          {steps.map((_, k) => <span key={k} className={`h-1.5 rounded-full transition-all ${k === i ? "w-5 bg-primary" : "w-1.5 bg-hairline"}`} />)}
        </div>
        <div className="mt-4 flex items-center justify-between gap-3">
          {!last ? <button onClick={close} className="t-caption text-ink-60 hover:text-ink">Skip tutorial</button> : <span />}
          <div className="flex gap-2">
            {i > 0 && <button onClick={back} className="btn btn-light btn-sm">Back</button>}
            <button onClick={next} className="btn btn-primary btn-sm" autoFocus>{last ? "Start reading" : i === 0 ? "Show me" : "Next"}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
