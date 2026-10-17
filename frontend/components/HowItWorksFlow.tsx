"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRef } from "react";

gsap.registerPlugin(useGSAP);

const STAGES = [
  { title: "Collect", caption: "Every night, ParhLo collects new stories from trusted outlets in Pakistan and around the world." },
  { title: "Sort", caption: "AI sorts each story into a topic, rates how important it is, and removes things that aren't news." },
  { title: "Match", caption: "Every story is compared with what you like, follow and read." },
  { title: "Check", caption: "Summaries are written from the original article, then checked against it." },
  { title: "Print", caption: "Your paper is laid out: a short edition that ends, ready every morning." },
];

const ICONS = [
  <path key="0" d="M4 6h16M4 12h16M4 18h10" />,
  <path key="1" d="M4 5h16l-6 7v6l-4 2v-8L4 5Z" />,
  <><circle key="a" cx="12" cy="12" r="8" /><circle key="b" cx="12" cy="12" r="3" /></>,
  <path key="3" d="m5 12 4.5 4.5L19 7" />,
  <><path key="a" d="M5 4h14v16H5z" /><path key="b" d="M8 8h8M8 12h8M8 16h5" /></>,
];

function Sources() {
  return (
    <div className="flex flex-col items-start gap-1.5">
      {["Dawn", "BBC News", "Geo News", "The Verge"].map((s) => (
        <span key={s} className="src rounded-full bg-parchment px-2.5 py-1 text-[11px] font-medium text-ink-80">{s}</span>
      ))}
    </div>
  );
}

function Sort() {
  const rows = [
    { t: "PCB names T20 squad", tag: "Cricket" },
    { t: "Quiz: who said it?", tag: "Not news", junk: true },
    { t: "SBP keeps rate at 11%", tag: "Economy" },
  ];
  return (
    <div className="flex flex-col gap-2">
      {rows.map((r) => (
        <div key={r.t} className={`sort-row flex items-center justify-between gap-1.5 rounded-[8px] bg-parchment px-2 py-1.5 ${r.junk ? "junk" : ""}`}>
          <span className="sort-text truncate text-[10.5px] text-ink-80">{r.t}</span>
          <span className={`tag flex-none rounded-full px-1.5 py-0.5 text-[9.5px] font-semibold ${r.junk ? "bg-[#fff2f2] text-danger" : "bg-[#e8f1fb] text-primary"}`}>{r.tag}</span>
        </div>
      ))}
    </div>
  );
}

function Match() {
  const bars = [{ l: "Cricket", v: 92 }, { l: "Economy", v: 64 }, { l: "Fashion", v: 8 }];
  return (
    <div className="flex flex-col gap-2.5">
      {bars.map((b) => (
        <div key={b.l}>
          <div className="flex justify-between text-[10.5px] text-ink-80"><span>{b.l}</span><span className="tabular-nums text-ink-48">{b.v}%</span></div>
          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-parchment">
            <div className="match-bar h-full rounded-full" style={{ width: `${b.v}%`, background: b.v > 50 ? "#0066cc" : "#d2d2d7" }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function Check() {
  return (
    <div>
      {[100, 92, 70].map((w, i) => <div key={i} className="check-line mb-2 h-1.5 rounded-full bg-[#d2d2d7]" style={{ width: `${w}%` }} />)}
      <span className="check-badge mt-2 inline-flex items-center gap-1 rounded-full bg-[#eaf6ec] px-2 py-1 text-[10.5px] font-semibold text-success">✓ Checked against source</span>
    </div>
  );
}

function Paper() {
  return (
    <div className="paper-mini rounded-[8px] border border-hairline bg-white p-2 shadow-[0_6px_20px_-10px_rgba(0,0,0,.3)]">
      <p className="pp masthead text-center text-[15px]">ParhLo</p>
      <div className="pp double-rule mt-1" />
      <div className="pp mt-1.5 h-8 rounded-[4px] bg-gradient-to-br from-[#2997ff] to-[#0066cc]" />
      <div className="pp mt-1.5 h-1.5 w-4/5 rounded-full bg-ink" />
      <div className="mt-1.5 grid grid-cols-2 gap-1.5">
        {[0, 1].map((c) => (
          <div key={c} className="pp space-y-1">
            <div className="h-1 rounded-full bg-[#d2d2d7]" /><div className="h-1 w-4/5 rounded-full bg-[#d2d2d7]" /><div className="h-1 rounded-full bg-[#d2d2d7]" />
          </div>
        ))}
      </div>
    </div>
  );
}

const MINIS = [Sources, Sort, Match, Check, Paper];

/** Looping diagram of the nightly pipeline: each stage lights up and plays its own small animation. */
export function HowItWorksFlow() {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    const q = gsap.utils.selector(root);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    gsap.from(q(".stage"), { y: 24, opacity: 0, stagger: 0.08, duration: 0.6, ease: "power3.out" });
    if (reduce) {
      gsap.set(q(".caption-0"), { opacity: 1 });
      return;
    }

    const tl = gsap.timeline({ repeat: -1, repeatDelay: 0.4, delay: 0.8, defaults: { ease: "power3.out" } });
    const on = (i: number, at: number | string) => {
      tl.to(q(".stage"), { borderColor: "rgba(0,0,0,0)", boxShadow: "0 0 0 0 rgba(0,0,0,0)", scale: 1, duration: 0.3 }, at)
        .to(q(`.stage-${i}`), { borderColor: "#0071e3", boxShadow: "0 18px 40px -18px rgba(0,102,204,.45)", scale: 1.03, duration: 0.4 }, "<")
        .to(q(".node"), { backgroundColor: (k: number) => (k <= i ? "#0066cc" : "#d2d2d7"), duration: 0.3 }, "<")
        .to(q(".track-fill"), { width: `${(i / (STAGES.length - 1)) * 100}%`, duration: 0.6, ease: "power2.inOut" }, "<")
        .to(q(".cap"), { opacity: 0, y: -6, duration: 0.2 }, "<")
        .fromTo(q(`.caption-${i}`), { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.4 }, ">-0.05");
    };

    // reset every loop
    tl.set(q(".src"), { x: -30, opacity: 0 })
      .set(q(".tag"), { scale: 0, opacity: 0 })
      .set(q(".sort-row"), { opacity: 1, x: 0 })
      .set(q(".sort-text"), { textDecoration: "none" })
      .set(q(".match-bar"), { scaleX: 0, transformOrigin: "left" })
      .set(q(".check-line"), { scaleX: 0, transformOrigin: "left" })
      .set(q(".check-badge"), { scale: 0.6, opacity: 0 })
      .set(q(".pp"), { y: 10, opacity: 0 })
      .set(q(".track-fill"), { width: "0%" });

    on(0, ">");
    tl.to(q(".src"), { x: 0, opacity: 1, stagger: 0.12, duration: 0.45 }, "<");
    on(1, "+=0.9");
    tl.to(q(".tag"), { scale: 1, opacity: 1, stagger: 0.18, duration: 0.35, ease: "back.out(2)" }, "<0.2")
      .to(q(".junk .sort-text"), { textDecoration: "line-through", duration: 0.01 }, "+=0.2")
      .to(q(".junk"), { x: 24, opacity: 0, duration: 0.5, ease: "power2.in" }, "+=0.35");
    on(2, "+=0.6");
    tl.to(q(".match-bar"), { scaleX: 1, stagger: 0.15, duration: 0.8 }, "<0.2");
    on(3, "+=0.8");
    tl.to(q(".check-line"), { scaleX: 1, stagger: 0.15, duration: 0.45 }, "<0.2")
      .to(q(".check-badge"), { scale: 1, opacity: 1, duration: 0.4, ease: "back.out(2.5)" }, "+=0.1");
    on(4, "+=0.8");
    tl.to(q(".pp"), { y: 0, opacity: 1, stagger: 0.09, duration: 0.4 }, "<0.2")
      .to({}, { duration: 2.2 });
  }, { scope: root });

  return (
    <div ref={root} className="mx-auto max-w-[1080px] px-4">
      <div className="relative mx-[10%] hidden h-6 items-center sm:flex" aria-hidden>
        <div className="absolute inset-x-0 top-1/2 h-[2px] -translate-y-1/2 bg-[#e0e0e0]" />
        <div className="track-fill absolute left-0 top-1/2 h-[2px] w-0 -translate-y-1/2 bg-primary" />
        <div className="relative flex w-full justify-between">
          {STAGES.map((s, i) => <span key={s.title} className="node flex h-6 w-6 items-center justify-center rounded-full bg-[#d2d2d7] text-[11px] font-semibold text-white">{i + 1}</span>)}
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-5">
        {STAGES.map((s, i) => {
          const Mini = MINIS[i];
          return (
            <div key={s.title} className={`stage stage-${i} rounded-[18px] border-2 border-transparent bg-canvas p-4`}>
              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#e8f1fb] text-primary">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{ICONS[i]}</svg>
                </span>
                <p className="t-body font-semibold">{s.title}</p>
              </div>
              <div className="mt-4 h-[124px] overflow-hidden"><Mini /></div>
            </div>
          );
        })}
      </div>

      <div className="relative mx-auto mt-8 min-h-[96px] max-w-[640px] text-center" aria-live="off">
        {STAGES.map((s, i) => (
          <p key={s.title} className={`cap caption-${i} absolute inset-x-0 top-0 t-lead text-ink-60 opacity-0`}>{s.caption}</p>
        ))}
      </div>
    </div>
  );
}
