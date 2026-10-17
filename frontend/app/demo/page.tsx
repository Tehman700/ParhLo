"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ErrorNote, Spinner, TopBar } from "@/components/ui";
import { request } from "@/lib/api";
import { useSession } from "@/lib/auth";

type Persona = { id: string; name: string; city: string; about: string | null; top_topics: string[] | null };

export default function DemoPage() {
  const router = useRouter();
  const { setDemoUser } = useSession();
  const [personas, setPersonas] = useState<Persona[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    request<Persona[]>("/api/demo/personas").then(setPersonas).catch((e) => setError(e.message));
  }, []);

  useGSAP(() => {
    if (personas) gsap.from(".persona", { y: 24, opacity: 0, stagger: 0.08, duration: 0.6, ease: "power3.out" });
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
    <div ref={root}>
      <TopBar />
      <main className="mx-auto max-w-[900px] px-4 py-16">
        <p className="label">Try ParhLo</p>
        <h1 className="display mt-2 text-[40px]">Read as a demo reader</h1>
        <p className="mt-3 max-w-xl text-ink-60">Start fresh with your own interests in 60 seconds, or open the paper of a reader who already has one.</p>

        <button className="btn btn-primary mt-8 !px-7 !py-3.5" onClick={fresh} disabled={busy}>
          {busy ? <Spinner dark label="Setting up…" /> : "Start fresh — build my paper"}
        </button>

        <div className="mt-12">
          <ErrorNote error={error} />
          {!personas && !error && <Spinner label="Loading readers…" />}
          <div className="grid gap-4 sm:grid-cols-2">
            {(personas ?? []).map((p) => (
              <button key={p.id} className="persona card text-left transition-shadow hover:shadow-[0_10px_30px_-12px_rgba(0,0,0,.25)]"
                onClick={() => { setDemoUser(p.id); router.push("/paper"); }}>
                <div className="flex items-center gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-full bg-ink font-masthead text-[20px] text-sun">{p.name[0]}</span>
                  <div>
                    <div className="text-[19px] font-semibold">{p.name}</div>
                    <div className="caption text-ink-48">{p.city}</div>
                  </div>
                </div>
                {p.about && <p className="mt-3 font-serif text-[15px] italic text-ink-60">&ldquo;{p.about}&rdquo;</p>}
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {(p.top_topics ?? []).slice(0, 4).map((t) => (
                    <span key={t} className="rounded-full bg-newsprint px-2.5 py-1 text-[12px] font-semibold text-ink-60">{t}</span>
                  ))}
                </div>
                <p className="mt-4 text-[14px] font-semibold text-primary">Open {p.name.split(" ")[0]}&apos;s paper →</p>
              </button>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
