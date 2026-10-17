"use client";

import gsap from "gsap";
import { useCallback, useEffect, useRef, useState } from "react";
import { TOUR_VIDEO } from "@/lib/site";
import { MotionLoop } from "./MotionLoop";

/** Landing-page product tour: a muted inline preview, a "Watch the tour" button and a lightbox player.
 *  /#tour opens the lightbox directly (a shareable link). Until TOUR_VIDEO is set, the motion loop stands in. */
const OPEN_EVENT = "parhlo:open-tour";
const HASH = "#tour";
const hasVideo = () => Boolean(TOUR_VIDEO.mp4 || TOUR_VIDEO.webm);

function Sources() {
  return (
    <>
      {TOUR_VIDEO.webm && <source src={TOUR_VIDEO.webm} type="video/webm" />}
      {TOUR_VIDEO.mp4 && <source src={TOUR_VIDEO.mp4} type="video/mp4" />}
    </>
  );
}

/** Inline, muted and looping (sits in a landing section). */
export function TourPreview({ bg = "ffffff" }: { bg?: string }) {
  if (!hasVideo()) return <MotionLoop bg={bg} />;
  return (
    <video className="aspect-video w-full rounded-[18px] bg-parchment object-cover" autoPlay muted loop playsInline
      poster={TOUR_VIDEO.poster} aria-label="ParhLo product tour (preview)">
      <Sources />
    </video>
  );
}

export function WatchTourButton({ className = "" }: { className?: string }) {
  return (
    <button type="button" className={`link inline-flex items-center gap-2 t-body ${className}`}
      onClick={() => { history.pushState(null, "", HASH); window.dispatchEvent(new Event(OPEN_EVENT)); }}>
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-white" aria-hidden>
        <svg width="10" height="12" viewBox="0 0 10 12"><path d="M1 1.2v9.6L9.2 6z" fill="currentColor" /></svg>
      </span>
      Watch the tour
    </button>
  );
}

/** Full-screen player. Esc, the ✕ or a click outside closes it (and pauses the video). */
export function TourLightbox() {
  const [open, setOpen] = useState(false);
  const panel = useRef<HTMLDivElement>(null);
  const closeBtn = useRef<HTMLButtonElement>(null);

  const close = useCallback(() => {
    setOpen(false);
    if (location.hash === HASH) history.replaceState(null, "", location.pathname + location.search);
  }, []);

  useEffect(() => {
    const sync = () => setOpen(location.hash === HASH);
    const openNow = () => setOpen(true);
    sync();
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    window.addEventListener(OPEN_EVENT, openNow);
    return () => { window.removeEventListener("hashchange", sync); window.removeEventListener("popstate", sync); window.removeEventListener(OPEN_EVENT, openNow); };
  }, []);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const key = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("keydown", key);
    closeBtn.current?.focus();
    if (panel.current) gsap.fromTo(panel.current, { opacity: 0, y: 24, scale: 0.97 }, { opacity: 1, y: 0, scale: 1, duration: 0.4, ease: "power3.out" });
    return () => { document.body.style.overflow = prev; window.removeEventListener("keydown", key); };
  }, [open, close]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[95] flex items-center justify-center bg-black/80 p-4 sm:p-8" role="dialog" aria-modal="true"
      aria-label="ParhLo product tour" onMouseDown={(e) => e.target === e.currentTarget && close()}>
      <div ref={panel} className="w-full max-w-[1040px]">
        <div className="mb-3 flex items-center justify-between text-white">
          <p className="t-body font-semibold">ParhLo, in a short tour</p>
          <button ref={closeBtn} onClick={close} aria-label="Close the tour"
            className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-[18px] hover:bg-white/20">✕</button>
        </div>
        <div className="overflow-hidden rounded-[18px] bg-canvas">
          {hasVideo() ? (
            <video className="aspect-video w-full bg-black" controls autoPlay playsInline poster={TOUR_VIDEO.poster}>
              <Sources />
            </video>
          ) : (
            <MotionLoop bg="ffffff" wide />
          )}
        </div>
        <p className="mt-3 text-center t-caption text-white/60">Press Esc or click outside to close.</p>
      </div>
    </div>
  );
}
