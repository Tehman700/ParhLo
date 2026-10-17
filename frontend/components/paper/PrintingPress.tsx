"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useEffect, useRef, useState } from "react";
import { LogoMark } from "../Logo";

gsap.registerPlugin(useGSAP);

const STAGES = [
  "Collecting today's articles",
  "Choosing stories for you",
  "Grouping stories from different outlets",
  "Summarizing each article",
  "Checking summaries against their sources",
  "Adding weather, air quality and rates",
  "Laying out your paper",
];

/** Loader while today's paper is being prepared. */
export function PrintingPress() {
  const root = useRef<HTMLDivElement>(null);
  const [stage, setStage] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 3200);
    return () => clearInterval(t);
  }, []);

  useGSAP(() => {
    gsap.from(".press-mark", { scale: 0.7, opacity: 0, duration: 0.6, ease: "power3.out" });
    gsap.fromTo(".press-mark .logo-sun", { y: 14 }, { y: 0, duration: 1.4, ease: "sine.inOut", repeat: -1, yoyo: true });
    const tl = gsap.timeline({ repeat: -1, repeatDelay: 0.4 });
    tl.set(".press-line", { scaleX: 0 }).to(".press-line", { scaleX: 1, duration: 0.35, stagger: 0.06, ease: "power1.out" });
  }, { scope: root });

  useGSAP(() => {
    gsap.fromTo(".press-stage", { y: 8, opacity: 0 }, { y: 0, opacity: 1, duration: 0.4 });
  }, { scope: root, dependencies: [stage] });

  return (
    <div ref={root} className="flex min-h-screen flex-col items-center justify-center bg-parchment px-6 text-center">
      <LogoMark size={72} className="press-mark" />
      <h2 className="t-section mt-8">Preparing your paper</h2>
      <p className="press-stage mt-2 h-6 t-body text-ink-60">{STAGES[stage]}…</p>
      <div className="mt-10 w-full max-w-[300px] space-y-2.5">
        {[100, 86, 94, 70].map((w, i) => (
          <div key={i} className="press-line h-1.5 origin-left rounded-full bg-ink/10" style={{ width: `${w}%` }} />
        ))}
      </div>
      <p className="mt-10 t-caption text-ink-48">Your first paper takes about a minute.</p>
    </div>
  );
}
