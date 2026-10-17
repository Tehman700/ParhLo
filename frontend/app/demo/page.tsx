"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ErrorNote, Spinner, TopBar } from "@/components/ui";
import { request } from "@/lib/api";
import { useSession } from "@/lib/auth";
import { topicLabel } from "@/lib/topics";

gsap.registerPlugin(useGSAP);

type Persona = { id: string; name: string; city: string; about: string | null; top_topics: string[] | null };

export default function DemoPage() {
  const router = useRouter();
  const { setDemoUser, user } = useSession();
  const [personas, setPersonas] = useState<Persona[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    request<Persona[]>("/api/demo/personas").then(setPersonas).catch((e) => setError(e.message));
  }, []);

  useGSAP(() => {
    gsap.from(".demo-head > *", { y: 20, opacity: 0, stagger: 0.08, duration: 0.6, ease: "power3.out" });
  }, { scope: root });

  useGSAP(() => {
    if (personas?.length) gsap.from(".persona", { y: 24, opacity: 0, stagger: 0.08, duration: 0.6, ease: "power3.out", delay: 0.2 });
  }, { scope: root, dependencies: [personas] });

  async function fresh() {
    setBusy(true);
    try {
      const { id } = await request<{ id: string }>("/api/demo/start", { method: "POST" });
      setDemoUser(id);
      router.push("/onboarding");
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <div ref={root} className="min-h-screen bg-parchment">
      <TopBar />
      <main className="mx-auto max-w-[980px] px-4 py-20">
        <div className="demo-head text-center">
          <h1 className="t-hero">Try ParhLo.</h1>
          <p className="t-lead mx-auto mt-4 max-w-xl text-ink-60">No account needed. Set up your own paper, or open one that&apos;s ready.</p>
          {user ? (
            <div className="mx-auto mt-8 max-w-xl rounded-[18px] bg-canvas p-6">
              <p className="t-body">You&apos;re signed in as {user.email}, so you already have your own paper.</p>
              <Link href="/paper" className="btn btn-primary mt-5">Open my paper</Link>
            </div>
          ) : (
            <div className="mt-8">
              <button className="btn btn-primary" onClick={fresh} disabled={busy}>
                {busy ? <Spinner dark label="Setting up" /> : "Set up my own paper"}
              </button>
            </div>
          )}
        </div>

        {!user && <div className="mt-20">
          <h2 className="t-tagline text-center">Or open a ready paper</h2>
          <div className="mt-2 text-center"><ErrorNote error={error} /></div>
          {!personas && !error && <div className="mt-6 text-center"><Spinner label="Loading" /></div>}
          <div className="mt-8 grid gap-5 sm:grid-cols-2">
            {(personas ?? []).map((p) => (
              <button key={p.id} className="persona rounded-[18px] bg-canvas p-7 text-left transition-shadow hover:shadow-[0_8px_30px_-12px_rgba(0,0,0,.18)]"
                onClick={() => { setDemoUser(p.id); router.push("/paper"); }}>
                <div className="flex items-center gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-full bg-parchment text-[19px] font-semibold">{p.name[0]}</span>
                  <div>
                    <p className="t-tagline !text-[19px]">{p.name}</p>
                    <p className="t-caption text-ink-60">{p.city}</p>
                  </div>
                </div>
                {p.about && <p className="mt-4 t-body text-ink-60">{p.about}</p>}
                <p className="mt-4 t-caption text-ink-60">{(p.top_topics ?? []).slice(0, 4).map(topicLabel).join(" · ")}</p>
                <p className="mt-5 t-body text-primary">Open paper ›</p>
              </button>
            ))}
          </div>
        </div>}
      </main>
    </div>
  );
}
