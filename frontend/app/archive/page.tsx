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
    if (items?.length) gsap.from(".archive-card", { y: 30, opacity: 0, stagger: 0.07, duration: 0.6, ease: "power3.out" });
  }, { scope: root, dependencies: [items] });

  return (
    <div ref={root} className="min-h-screen bg-parchment">
      <TopBar />
      <main className="mx-auto max-w-[980px] px-4 py-16">
        <h1 className="t-display">Past papers</h1>
        <p className="t-lead mt-3 text-ink-60">Every paper you&apos;ve received, newest first.</p>
        <div className="mt-8"><ErrorNote error={error} /></div>
        {!items && !error && <Spinner label="Loading" />}
        {items && !items.length && <p className="t-body text-ink-60">No papers yet. <Link href="/paper" className="link">Get today&apos;s paper</Link></p>}
        <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {(items ?? []).map((e) => (
            <Link key={e.id} href={`/paper/${e.edition_date}`} className="archive-card block rounded-[18px] bg-canvas p-6 transition-shadow hover:shadow-[0_8px_30px_-12px_rgba(0,0,0,.18)]">
              <div className="flex justify-between t-caption text-ink-60">
                <span>{formatDate(e.edition_date, { weekday: "long", day: "numeric", month: "long" })}</span><span>No. {e.number}</span>
              </div>
              <div className="masthead mt-4 text-center text-[30px]">ParhLo</div>
              <div className="double-rule mt-2" />
              <p className="headline mt-4 text-[19px]">{e.lead_headline ?? "Your paper"}</p>
              <p className="mt-2 line-clamp-3 t-caption text-ink-60">{e.editor_note}</p>
              <p className="mt-4 t-caption text-primary">{e.stories} stories · Read ›</p>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
