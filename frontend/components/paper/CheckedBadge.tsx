"use client";

import gsap from "gsap";
import Link from "next/link";
import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Story } from "@/lib/api";

const W = 316; // popup width

/** "✓ Checked against source" with a hover card explaining Jev. Hovering opens it, moving the pointer away
 *  closes it (the pointer can travel into the card to click "How ParhLo uses Jev"). Tap/keyboard toggle too.
 *  The card is portalled to <body> because story cards clip their content. */
export function CheckedBadge({ story }: { story: Story }) {
  const c = story.check;
  const pct = c?.confidence != null ? Math.round(c.confidence * 100) : null;
  const byJev = c?.by !== "llm";
  const id = useId();
  const btn = useRef<HTMLButtonElement>(null);
  const card = useRef<HTMLDivElement>(null);
  const timer = useRef<number | undefined>(undefined);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ left: number; y: number; arrow: number; below: boolean } | null>(null);

  const show = useCallback(() => { window.clearTimeout(timer.current); setOpen(true); }, []);
  const hide = useCallback(() => { window.clearTimeout(timer.current); timer.current = window.setTimeout(() => setOpen(false), 140); }, []);

  const place = useCallback(() => {
    const r = btn.current?.getBoundingClientRect();
    if (!r) return;
    const below = r.top < 250; // not enough room above → open below
    const left = Math.min(Math.max(12, r.left - 12), window.innerWidth - W - 12);
    // Above: anchor by `bottom` so GSAP's entrance transform can't fight a translateY anchor.
    setPos({ left, y: below ? r.bottom + 12 : window.innerHeight - r.top + 12, arrow: Math.min(W - 24, Math.max(16, r.left + 22 - left)), below });
  }, []);

  useLayoutEffect(() => { if (open) place(); }, [open, place]);
  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("scroll", close, { passive: true });
    window.addEventListener("resize", close);
    window.addEventListener("keydown", esc);
    return () => { window.removeEventListener("scroll", close); window.removeEventListener("resize", close); window.removeEventListener("keydown", esc); };
  }, [open]);
  useEffect(() => {
    if (open && pos && card.current)
      gsap.fromTo(card.current, { opacity: 0, y: pos.below ? -6 : 6, scale: 0.97 }, { opacity: 1, y: 0, scale: 1, duration: 0.22, ease: "power2.out" });
  }, [open, pos]);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  return (
    <>
      <button ref={btn} type="button" data-tour="checked" aria-describedby={open ? id : undefined} aria-expanded={open}
        onMouseEnter={show} onMouseLeave={hide} onFocus={show} onBlur={hide} onClick={() => (open ? setOpen(false) : show())}
        className="t-caption font-semibold text-success underline decoration-success/30 decoration-dotted underline-offset-4 hover:decoration-success">
        ✓ Checked against source{pct != null ? ` · ${pct}%` : ""}
      </button>
      {open && pos && createPortal(
        <div ref={card} id={id} role="tooltip" onMouseEnter={show} onMouseLeave={hide}
          className="fixed z-[80] rounded-[16px] bg-ink p-4 text-left text-white shadow-[0_18px_48px_-12px_rgba(0,0,0,.45)]"
          style={{ left: pos.left, width: W, ...(pos.below ? { top: pos.y } : { bottom: pos.y }), transformOrigin: pos.below ? "top left" : "bottom left" }}>
          {/* hover bridge over the gap between badge and card */}
          <span aria-hidden className={`absolute left-0 right-0 h-4 ${pos.below ? "-top-4" : "-bottom-4"}`} />
          <span aria-hidden className={`absolute h-3 w-3 rotate-45 bg-ink ${pos.below ? "-top-1.5" : "-bottom-1.5"}`} style={{ left: pos.arrow }} />
          <div className="flex items-center gap-2.5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/brand/typesafe-jev.png" alt="" width={28} height={28} className="h-7 w-7 rounded-full" />
            <div>
              <p className="text-[15px] font-semibold leading-tight">{byJev ? "Checked by Jev" : "Checked by a second AI pass"}</p>
              <p className="t-fine text-white/60">{byJev ? "A decision model from TypeSafe" : "Used when Jev isn't available"}</p>
            </div>
          </div>
          <p className="mt-3 t-caption text-white/85">
            {byJev
              ? "After the summary was written, Jev read it next to the original article and looked for any claim, number, name or date the article doesn't support. It found none."
              : "A second AI pass compared the summary with the original article and found nothing it couldn't support."}
          </p>
          {pct != null && (
            <div className="mt-3">
              <div className="flex justify-between t-fine text-white/60"><span>Confidence</span><span>{pct}%{c?.ms ? ` · checked in ${c.ms} ms` : ""}</span></div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/15"><div className="h-full rounded-full bg-primary-on-dark" style={{ width: `${pct}%` }} /></div>
            </div>
          )}
          <Link href="/jev" className="mt-3 inline-block t-caption font-semibold text-primary-on-dark hover:underline">How ParhLo uses Jev ›</Link>
        </div>,
        document.body,
      )}
    </>
  );
}
