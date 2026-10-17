"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRef, type ReactNode } from "react";
import { TopBar } from "./ui";

gsap.registerPlugin(useGSAP);

export const CONTACT_EMAIL = "tehmanhassan@gmail.com";

/** Long-form text page (privacy, terms, about): parchment header, white reading column. */
export function DocPage({ title, lead, updated, children }: { title: string; lead?: string; updated?: string; children: ReactNode }) {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(() => {
    gsap.from(".doc-head > *", { y: 20, opacity: 0, stagger: 0.08, duration: 0.6, ease: "power3.out" });
    gsap.from(".doc-body", { y: 24, opacity: 0, duration: 0.7, delay: 0.15, ease: "power3.out" });
  }, { scope: root });

  return (
    <div ref={root} className="min-h-screen bg-canvas">
      <TopBar />
      <header className="bg-parchment px-4 pb-14 pt-16">
        <div className="doc-head mx-auto max-w-[692px]">
          <h1 className="t-display">{title}</h1>
          {lead && <p className="t-lead mt-4 text-ink-60">{lead}</p>}
          {updated && <p className="mt-4 t-caption text-ink-48">Last updated {updated}</p>}
        </div>
      </header>
      <main className="doc-body doc mx-auto max-w-[692px] px-4 py-14">{children}</main>
    </div>
  );
}
