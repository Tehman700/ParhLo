"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorNote, Spinner, TopBar } from "@/components/ui";
import type { Edition, Me } from "@/lib/api";
import { useApi, useSession } from "@/lib/auth";
import { topicLabel } from "@/lib/topics";

gsap.registerPlugin(useGSAP);

const KIND_LABEL: Record<string, string> = {
  onboarding: "You chose", entity: "You follow", liked: "You liked", clicked: "You read", disliked: "Show less",
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
    if (!signedIn) return void router.replace("/sign-in");
    void load();
  }, [ready, signedIn, load, router]);

  useGSAP(() => {
    gsap.from(".page-head > *", { y: 20, opacity: 0, stagger: 0.08, duration: 0.6, ease: "power3.out" });
  }, { scope: root });

  useGSAP(() => {
    if (!me) return;
    gsap.from(".bar-fill", { width: 0, duration: 1.1, stagger: 0.04, ease: "power3.out" });
    gsap.from(".panel", { y: 24, opacity: 0, stagger: 0.1, duration: 0.6, ease: "power3.out" });
    gsap.from(".anchor-chip", { scale: 0.85, opacity: 0, stagger: 0.012, duration: 0.3, ease: "power2.out" });
  }, { scope: root, dependencies: [me] });

  async function learnAndReprint() {
    setBusy("Updating your interests");
    try {
      await api.post("/api/learn");
      setBusy("Preparing tomorrow's paper");
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
    <div ref={root} className="min-h-screen bg-parchment">
      <TopBar />
      <main className="mx-auto max-w-[980px] px-4 py-16">
        <div className="page-head">
          <h1 className="t-display">Your interests</h1>
          <p className="t-lead mt-3 max-w-2xl text-ink-60">What you read, skip and like changes this. You can remove anything here.</p>
          {me && (
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <button className="btn btn-primary" onClick={learnAndReprint} disabled={!!busy}>
                {busy ? <Spinner dark label={busy} /> : "Update and see tomorrow's paper"}
              </button>
              <span className="t-caption text-ink-60">This happens automatically every night.</span>
            </div>
          )}
        </div>
        <div className="mt-6"><ErrorNote error={error} /></div>
        {!me && !error && <Spinner label="Loading" />}

        {me && (
          <>
            <div className="mt-10 grid gap-5 lg:grid-cols-[1.3fr_1fr]">
              <section className="panel rounded-[18px] bg-canvas p-7">
                <h2 className="t-tagline">Topics</h2>
                <div className="mt-6 space-y-4">
                  {topics.map(([slug, w]) => (
                    <div key={slug} className="grid grid-cols-[140px_1fr_36px] items-center gap-3 t-caption">
                      <span className="truncate t-body">{topicLabel(slug)}</span>
                      <div className="h-2 overflow-hidden rounded-full bg-parchment">
                        <div className="bar-fill h-full rounded-full" style={{ width: `${Math.round(w * 100)}%`, background: w >= 0.5 ? "#0066cc" : w >= 0.25 ? "#2997ff" : "#d2d2d7" }} />
                      </div>
                      <span className="text-right tabular-nums text-ink-48">{Math.round(w * 100)}</span>
                    </div>
                  ))}
                </div>
              </section>

              <div className="space-y-5">
                <section className="panel rounded-[18px] bg-canvas p-7">
                  <h2 className="t-tagline">Recent changes</h2>
                  {latest ? (
                    <ul className="mt-5 space-y-4">
                      {latest.changes.filter((c) => c.topic).map((c) => {
                        const up = (c.to ?? 0) > (c.from ?? 0);
                        return (
                          <li key={c.topic} className="flex gap-3">
                            <span className={`mt-0.5 ${up ? "text-primary" : "text-danger"}`}>{up ? "▲" : "▼"}</span>
                            <div>
                              <p className="t-body font-semibold">{c.label}: {Math.round((c.from ?? 0) * 100)} → {Math.round((c.to ?? 0) * 100)}</p>
                              <p className="t-caption text-ink-60">{c.why}.</p>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  ) : <p className="mt-4 t-body text-ink-60">Read today&apos;s paper, then press the button above to see what changes.</p>}
                </section>
                <section className="panel rounded-[18px] bg-canvas p-7">
                  <h2 className="t-tagline">Settings</h2>
                  <dl className="mt-4 space-y-2 t-body">
                    <div className="flex justify-between"><dt className="text-ink-60">City</dt><dd>{me.user.city}</dd></div>
                    <div className="flex justify-between"><dt className="text-ink-60">Reading time</dt><dd>{me.user.reading_minutes} minutes</dd></div>
                    <div className="flex justify-between"><dt className="text-ink-60">Pakistan news</dt><dd>{Math.round(me.user.region_mix * 100)}%</dd></div>
                    {!!me.profile?.entities.length && <div className="flex justify-between gap-4"><dt className="text-ink-60">Following</dt><dd className="text-right">{me.profile.entities.join(", ")}</dd></div>}
                  </dl>
                </section>
              </div>
            </div>

            <section className="panel mt-5 rounded-[18px] bg-canvas p-7">
              <h2 className="t-tagline">What ParhLo remembers</h2>
              <p className="mt-1 t-caption text-ink-60">Each story in your paper is matched against these. Remove anything you don&apos;t want.</p>
              <div className="mt-5 flex flex-wrap gap-2">
                {me.anchors.map((a) => (
                  <span key={a.id} className={`anchor-chip inline-flex max-w-[360px] items-center gap-2 rounded-full px-3.5 py-1.5 t-caption ${a.weight < 0 ? "bg-[#fff2f2] text-danger" : "bg-parchment"}`}>
                    <span className="text-ink-48">{KIND_LABEL[a.kind] ?? a.kind}</span>
                    <span className="truncate">{a.label}</span>
                    <button aria-label={`Remove ${a.label}`} className="text-ink-48 hover:text-ink" onClick={() => removeAnchor(a.id)}>✕</button>
                  </span>
                ))}
                {!me.anchors.length && <p className="t-body text-ink-60">Nothing yet.</p>}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
