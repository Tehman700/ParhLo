"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorNote, Spinner, TopBar } from "@/components/ui";
import type { Edition, Me } from "@/lib/api";
import { useApi, useSession } from "@/lib/auth";
import { topicLabel } from "@/lib/topics";

const KIND_STYLE: Record<string, string> = {
  onboarding: "bg-ink text-white", entity: "bg-sun text-ink", liked: "bg-[#e9f6ec] text-success",
  clicked: "bg-[#e8f1fb] text-primary", disliked: "bg-[#fff1f0] text-danger",
};

export default function Profile() {
  const router = useRouter();
  const api = useApi();
  const { ready, signedIn } = useSession();
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const root = useRef<HTMLDivElement>(null);

  const load = useCallback(() => api.get<Me>("/api/me").then(setMe).catch((e) => setError(e.message)), [api]);
  useEffect(() => {
    if (!ready) return;
    if (!signedIn) return void router.replace("/");
    void load();
  }, [ready, signedIn, load, router]);

  useGSAP(() => {
    if (!me) return;
    gsap.from(".bar-fill", { width: 0, duration: 1.1, stagger: 0.04, ease: "power3.out" });
    gsap.from(".change-row", { x: -20, opacity: 0, stagger: 0.08, duration: 0.5 });
    gsap.from(".anchor-chip", { scale: 0.7, opacity: 0, stagger: 0.015, duration: 0.3, ease: "back.out(2)" });
  }, { scope: root, dependencies: [me] });

  async function learnAndReprint() {
    setBusy("Learning from your reading…");
    try {
      await api.post("/api/learn");
      setBusy("Printing tomorrow's paper with what it learned…");
      const tomorrow = new Date(Date.now() + 5 * 3600_000 + 86400_000).toISOString().slice(0, 10);
      const ed = await api.post<Edition>("/api/editions/generate", { date: tomorrow, force: true });
      router.push(`/paper/${ed.edition_date}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(null);
    }
  }

  async function removeAnchor(id: number) {
    await api.del(`/api/me/anchors/${id}`);
    setMe((m) => (m ? { ...m, anchors: m.anchors.filter((a) => a.id !== id) } : m));
  }

  const topics = Object.entries(me?.profile?.topics ?? {}).sort((a, b) => b[1] - a[1]);
  const latest = me?.snapshots.find((s) => s.changes.some((c) => c.topic));

  return (
    <div ref={root} className="min-h-screen">
      <TopBar />
      <main className="mx-auto max-w-[1100px] px-4 py-14">
        <p className="label">Your memory</p>
        <h1 className="display mt-2 text-[40px]">What your paper knows about you</h1>
        <p className="mt-2 max-w-2xl text-ink-60">Every read, skip and reaction updates this. Nothing is hidden — remove anything you don&apos;t want it to remember.</p>
        <div className="mt-6"><ErrorNote error={error} /></div>
        {!me && !error && <Spinner label="Loading your memory…" />}

        {me && (
          <>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button className="btn btn-primary" onClick={learnAndReprint} disabled={!!busy}>
                {busy ? <Spinner dark label={busy} /> : "Learn from today & print tomorrow's paper"}
              </button>
              <span className="caption text-ink-48">Normally this runs automatically every night at 5:30.</span>
            </div>

            <div className="mt-10 grid gap-6 lg:grid-cols-[1.3fr_1fr]">
              <section className="card">
                <h2 className="text-[19px] font-semibold">Interest strength</h2>
                <div className="mt-5 space-y-3">
                  {topics.map(([slug, w]) => (
                    <div key={slug} className="grid grid-cols-[130px_1fr_40px] items-center gap-3 text-[14px]">
                      <span className="truncate">{topicLabel(slug)}</span>
                      <div className="h-2.5 overflow-hidden rounded-full bg-parchment">
                        <div className="bar-fill h-full rounded-full" style={{ width: `${Math.round(w * 100)}%`, background: w >= 0.5 ? "#0066cc" : w >= 0.25 ? "#2997ff" : "#d2d2d7" }} />
                      </div>
                      <span className="text-right tabular-nums text-ink-48">{Math.round(w * 100)}</span>
                    </div>
                  ))}
                </div>
              </section>

              <section className="space-y-6">
                <div className="card">
                  <h2 className="text-[19px] font-semibold">What changed recently</h2>
                  {latest ? (
                    <ul className="mt-4 space-y-3">
                      {latest.changes.filter((c) => c.topic).map((c) => (
                        <li key={c.topic} className="change-row flex gap-3">
                          <span className={`mt-0.5 text-[18px] ${c.to! > c.from! ? "text-success" : "text-danger"}`}>{c.to! > c.from! ? "▲" : "▼"}</span>
                          <div>
                            <p className="font-semibold">{c.label} {Math.round(c.from! * 100)} → {Math.round(c.to! * 100)}</p>
                            <p className="caption text-ink-60">{c.why}</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : <p className="mt-3 caption text-ink-60">Read today&apos;s paper — open, skip or react to stories — then press the button above to watch it learn.</p>}
                </div>
                <div className="card">
                  <h2 className="text-[19px] font-semibold">About you</h2>
                  <p className="mt-2 caption text-ink-60">{me.user.city} · {me.user.reading_minutes}-minute paper · {Math.round(me.user.region_mix * 100)}% Pakistan</p>
                  {me.profile?.about && <p className="mt-2 font-serif italic text-ink-80">&ldquo;{me.profile.about}&rdquo;</p>}
                  {!!me.profile?.entities.length && <p className="mt-2 caption">Following: {me.profile.entities.join(", ")}</p>}
                </div>
              </section>
            </div>

            <section className="card mt-6">
              <h2 className="text-[19px] font-semibold">Interest anchors <span className="caption font-normal text-ink-48">— the long-term memory each story is matched against</span></h2>
              <div className="mt-4 flex flex-wrap gap-2">
                {me.anchors.map((a) => (
                  <span key={a.id} className={`anchor-chip inline-flex max-w-[360px] items-center gap-2 rounded-full px-3 py-1.5 text-[13px] ${KIND_STYLE[a.kind] ?? "bg-parchment"}`}>
                    <span className="truncate">{a.label}</span>
                    <span className="opacity-60">{a.weight > 0 ? "+" : ""}{a.weight.toFixed(1)}</span>
                    <button aria-label={`Forget ${a.label}`} className="opacity-60 hover:opacity-100" onClick={() => removeAnchor(a.id)}>✕</button>
                  </span>
                ))}
              </div>
              <p className="mt-4 caption text-ink-48">Black = chose at onboarding · Gold = names you follow · Green = liked · Blue = read · Red = avoid</p>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
