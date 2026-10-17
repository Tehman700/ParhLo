"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { TopBar } from "./ui";

gsap.registerPlugin(useGSAP);

export type PolicySection = { id: string; title: string; body: ReactNode };

/** Long policy page: hero, "at a glance" cards, a contents list that follows you, and numbered sections. */
export function PolicyPage({ title, lead, updated, glance, sections }: {
  title: string; lead: string; updated: string;
  glance: { icon: string; title: string; text: string }[];
  sections: PolicySection[];
}) {
  const root = useRef<HTMLDivElement>(null);
  const [current, setCurrent] = useState(sections[0]?.id);

  useGSAP(() => {
    gsap.from(".pol-head > *", { y: 20, opacity: 0, stagger: 0.08, duration: 0.6, ease: "power3.out" });
    gsap.from(".glance", { y: 24, opacity: 0, stagger: 0.07, duration: 0.55, delay: 0.15, ease: "power3.out" });
  }, { scope: root });

  // highlight the section being read
  useEffect(() => {
    const io = new IntersectionObserver((entries) => {
      const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (visible[0]) setCurrent(visible[0].target.id);
    }, { rootMargin: "-80px 0px -60% 0px" });
    sections.forEach((s) => { const el = document.getElementById(s.id); if (el) io.observe(el); });
    return () => io.disconnect();
  }, [sections]);

  return (
    <div ref={root} className="min-h-screen bg-parchment">
      <TopBar />
      <header className="pb-10 pt-16">
        <div className="pol-head mx-auto max-w-[1024px] px-4">
          <p className="t-caption text-ink-48">Last updated {updated}</p>
          <h1 className="t-display mt-2">{title}</h1>
          <p className="t-lead mt-3 max-w-2xl text-ink-60">{lead}</p>
        </div>
      </header>

      <section className="mx-auto grid max-w-[1024px] gap-3 px-4 sm:grid-cols-2 lg:grid-cols-4" aria-label="At a glance">
        {glance.map((g) => (
          <div key={g.title} className="glance rounded-[18px] bg-canvas p-5">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#e8f1fb] text-[17px]" aria-hidden>{g.icon}</span>
            <p className="mt-3 t-body font-semibold">{g.title}</p>
            <p className="mt-1 t-caption text-ink-60">{g.text}</p>
          </div>
        ))}
      </section>

      <div className="mx-auto mt-10 grid max-w-[1024px] gap-8 px-4 pb-20 lg:grid-cols-[220px_1fr]">
        <nav className="hidden lg:block" aria-label="Contents">
          <div className="sticky top-16">
            <p className="t-fine font-semibold text-ink-48">On this page</p>
            <ol className="mt-3 space-y-1.5">
              {sections.map((s, i) => (
                <li key={s.id}>
                  <a href={`#${s.id}`} className={`block rounded-[8px] px-2 py-1 t-caption transition-colors ${current === s.id ? "bg-canvas font-semibold text-ink" : "text-ink-60 hover:text-ink"}`}>
                    {i + 1}. {s.title}
                  </a>
                </li>
              ))}
            </ol>
          </div>
        </nav>
        <main className="space-y-4">
          {sections.map((s, i) => (
            <section key={s.id} id={s.id} className="doc scroll-mt-16 rounded-[18px] bg-canvas p-6 sm:p-8">
              <h2 className="!mt-0 flex items-baseline gap-3"><span className="t-caption font-semibold text-primary">{String(i + 1).padStart(2, "0")}</span>{s.title}</h2>
              {s.body}
            </section>
          ))}
        </main>
      </div>
    </div>
  );
}

/** Two-column table that stays readable on phones (rows stack). */
export function PolicyTable({ head, rows }: { head: [string, string, string]; rows: [string, string, string][] }) {
  return (
    <div className="mt-4 overflow-hidden rounded-[12px] border border-hairline">
      <div className="hidden grid-cols-[1fr_1.4fr_1.6fr] gap-4 bg-parchment px-4 py-2.5 t-fine font-semibold text-ink-60 sm:grid">
        {head.map((h) => <span key={h}>{h}</span>)}
      </div>
      {rows.map((r) => (
        <div key={r[0]} className="grid gap-1 border-t border-divider px-4 py-3 first:border-t-0 sm:grid-cols-[1fr_1.4fr_1.6fr] sm:gap-4">
          <span className="t-caption font-semibold text-ink">{r[0]}</span>
          <span className="t-caption text-ink-80">{r[1]}</span>
          <span className="t-caption text-ink-60">{r[2]}</span>
        </div>
      ))}
    </div>
  );
}
