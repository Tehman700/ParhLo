"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ErrorNote, Spinner, TopBar, formatDate } from "@/components/ui";
import type { EditionSummary } from "@/lib/api";
import { useApi, useSession } from "@/lib/auth";

export default function Archive() {
  const router = useRouter();
  const api = useApi();
  const { ready, signedIn } = useSession();
  const [items, setItems] = useState<EditionSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ready) return;
    if (!signedIn) return void router.replace("/");
    api.get<EditionSummary[]>("/api/editions").then(setItems).catch((e) => setError(e.message));
  }, [ready, signedIn, api, router]);

  useGSAP(() => {
    if (items?.length) gsap.from(".archive-card", { y: 40, rotate: () => gsap.utils.random(-3, 3), opacity: 0, stagger: 0.07, duration: 0.7, ease: "power3.out" });
  }, { scope: root, dependencies: [items] });

  return (
    <div ref={root} className="min-h-screen">
      <TopBar />
      <main className="mx-auto max-w-[1100px] px-4 py-14">
        <p className="label">Archive</p>
        <h1 className="display mt-2 text-[40px]">Every paper you&apos;ve received</h1>
        <div className="mt-8"><ErrorNote error={error} /></div>
        {!items && !error && <Spinner label="Fetching your editions…" />}
        {items && !items.length && <p className="text-ink-60">No editions yet. <Link href="/paper" className="text-primary">Print today&apos;s paper</Link>.</p>}
        <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {(items ?? []).map((e) => (
            <Link key={e.id} href={`/paper/${e.edition_date}`} className="archive-card paper block rounded-[4px] p-5 shadow-[0_14px_40px_-18px_rgba(0,0,0,.35)] transition-transform hover:-translate-y-1">
              <div className="flex justify-between border-b border-ink pb-1 text-[11px] text-ink-60">
                <span>No. {e.number}</span><span>{formatDate(e.edition_date, { weekday: "short", day: "numeric", month: "short" })}</span>
              </div>
              <div className="py-2 text-center font-masthead text-[30px] font-black leading-none">Parh<span className="italic text-sun-deep">Lo</span></div>
              <div className="double-rule" />
              <p className="headline mt-3 text-[19px]">{e.lead_headline ?? "Your morning paper"}</p>
              <p className="mt-2 line-clamp-3 font-serif text-[14px] italic text-ink-60">{e.editor_note}</p>
              <p className="mt-3 text-[12px] font-semibold text-ink-48">{e.stories} stories · Read →</p>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
