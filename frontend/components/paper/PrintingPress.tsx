"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useEffect, useRef, useState } from "react";

const STAGES = [
  "Reading today's news from Dawn, Geo, BBC and 20 more…",
  "Ranking hundreds of stories for you…",
  "Grouping the same story across outlets…",
  "Summarising — only from the original articles…",
  "Fact-checking every summary against its source…",
  "Checking your weather, air and the rupee…",
  "Laying out your front page…",
];

/** The "printing your paper" loader: a sheet being set column by column. */
export function PrintingPress({ name }: { name?: string }) {
  const root = useRef<HTMLDivElement>(null);
  const [stage, setStage] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 3200);
    return () => clearInterval(t);
  }, []);

  useGSAP(() => {
    const tl = gsap.timeline({ repeat: -1, repeatDelay: 0.3 });
    tl.set(".press-line", { scaleX: 0 })
      .set(".press-mast", { scaleX: 0 })
      .to(".press-mast", { scaleX: 1, duration: 0.6, ease: "power2.out" })
      .to(".press-line", { scaleX: 1, duration: 0.35, stagger: 0.07, ease: "power1.out" })
      .to(".press-sheet", { y: -8, duration: 0.3, yoyo: true, repeat: 1 }, "+=0.2");
    gsap.from(".press-sheet", { rotateX: 60, opacity: 0, duration: 1, ease: "power3.out" });
  }, { scope: root });

  useGSAP(() => {
    gsap.fromTo(".press-stage", { y: 10, opacity: 0 }, { y: 0, opacity: 1, duration: 0.4 });
  }, { scope: root, dependencies: [stage] });

  return (
    <div ref={root} className="flex min-h-screen flex-col items-center justify-center bg-newsprint px-6 [perspective:1000px]">
      <div className="press-sheet w-full max-w-[420px] rounded-[4px] bg-white p-6 shadow-[0_30px_70px_-25px_rgba(0,0,0,.4)]">
        <div className="press-mast mx-auto h-5 w-2/3 origin-center rounded-sm bg-ink" />
        <div className="mx-auto mt-2 h-[3px] w-full border-t-[3px] border-double border-ink" />
        <div className="mt-4 grid grid-cols-3 gap-3">
          {[0, 1, 2].map((c) => (
            <div key={c} className="space-y-2">
              {Array.from({ length: c === 0 ? 9 : 7 }).map((_, i) => (
                <div key={i} className="press-line h-2 origin-left rounded-full bg-ink/20" style={{ width: `${70 + ((i * 37 + c * 11) % 30)}%` }} />
              ))}
            </div>
          ))}
        </div>
      </div>
      <h2 className="mt-10 text-center font-masthead text-[30px] font-bold">Printing {name ? `${name}'s` : "your"} paper</h2>
      <p className="press-stage mt-2 h-6 text-center text-ink-60">{STAGES[stage]}</p>
    </div>
  );
}
