"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { Edition } from "@/lib/api";
import { useApi } from "@/lib/auth";
import { ErrorNote } from "../ui";

gsap.registerPlugin(useGSAP);

const STEPS = [
  { at: 0, label: "Reading today's news" },
  { at: 6, label: "Choosing stories for you" },
  { at: 13, label: "Writing and checking summaries" },
  { at: 24, label: "Laying out your paper" },
];

/** Today's paper on the dashboard. If it isn't printed yet, it's built in the background while the reader looks around. */
export function PaperStatus({ welcome, name }: { welcome: boolean; name: string }) {
  const api = useApi();
  const root = useRef<HTMLDivElement>(null);
  const [edition, setEdition] = useState<Edition | null>(null);
  const [building, setBuilding] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    // Only show "preparing" if the paper isn't already there (an existing paper returns instantly).
    const slow = setTimeout(() => !cancelled && setBuilding(true), 700);
    api.post<Edition>("/api/editions/generate", {})
      .then((e) => !cancelled && setEdition(e))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => clearTimeout(slow));
    return () => { cancelled = true; clearTimeout(slow); };
  }, [api, attempt]);

  useEffect(() => {
    if (!building || edition || error) return;
    const t0 = Date.now();
    const tick = setInterval(() => setElapsed((Date.now() - t0) / 1000), 500);
    return () => clearInterval(tick);
  }, [building, edition, error]);

  useGSAP(() => {
    if (building && !edition) gsap.fromTo(".build-bar", { width: "4%" }, { width: "92%", duration: 40, ease: "power1.out" });
  }, { scope: root, dependencies: [building] });

  useGSAP(() => {
    if (!edition) return;
    gsap.to(".build-bar", { width: "100%", duration: 0.4, ease: "power2.out" });
    gsap.from(".ready > *", { y: 14, opacity: 0, stagger: 0.08, duration: 0.55, ease: "power3.out", delay: building ? 0.3 : 0 });
  }, { scope: root, dependencies: [edition] });

  const lead = edition?.stories.find((s) => s.id === edition.lead_id) ?? edition?.stories[0];
  const step = STEPS.filter((s) => elapsed >= s.at).length - 1;

  return (
    <section ref={root} className="panel overflow-hidden rounded-[18px] bg-canvas">
      {(building || !edition) && !error && (
        <div className="h-1 bg-parchment"><div className="build-bar h-full w-0 bg-primary" /></div>
      )}
      <div className="p-6 sm:p-8">
        {error ? (
          <ErrorNote error={error} onRetry={() => { setError(null); setElapsed(0); setAttempt((a) => a + 1); }} />
        ) : edition ? (
          <div className="ready flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="t-caption font-semibold text-success">✓ {welcome && edition.number === 1 ? "Your first paper is ready" : "Today's paper is ready"}</p>
              {lead && <p className="headline mt-2 text-[22px] sm:text-[24px]">{lead.headline}</p>}
              <p className="mt-1 t-caption text-ink-60">{edition.stories.length} stories · No. {edition.number}</p>
            </div>
            <div className="flex flex-none gap-3">
              <Link href="/paper" className="btn btn-primary">Read it now</Link>
              <Link href={`/paper/${edition.edition_date}/print`} className="btn btn-secondary">PDF</Link>
            </div>
          </div>
        ) : building ? (
          <div>
            <p className="t-tagline">{welcome ? `Welcome, ${name}. Your first paper is on its way.` : "Preparing today's paper"}</p>
            <p className="mt-1 t-caption text-ink-60">This takes about half a minute. Look around your dashboard meanwhile. We&apos;ll show it here when it&apos;s ready.</p>
            <ol className="mt-5 grid gap-2 sm:grid-cols-4">
              {STEPS.map((s, i) => (
                <li key={s.label} className={`flex items-center gap-2 t-caption transition-colors ${i < step ? "text-ink" : i === step ? "font-semibold text-primary" : "text-ink-48"}`}>
                  <span className={`flex h-5 w-5 flex-none items-center justify-center rounded-full text-[11px] ${i < step ? "bg-success text-white" : i === step ? "bg-primary text-white" : "bg-parchment"}`}>
                    {i < step ? "✓" : i + 1}
                  </span>
                  {s.label}
                </li>
              ))}
            </ol>
          </div>
        ) : (
          <p className="t-caption text-ink-48">Checking today&apos;s paper…</p>
        )}
      </div>
    </section>
  );
}
