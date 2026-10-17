"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Logo } from "@/components/Logo";
import { ErrorNote, Spinner } from "@/components/ui";
import { request, type Headline, type Me, type Topic } from "@/lib/api";
import { useApi, useSession } from "@/lib/auth";

gsap.registerPlugin(useGSAP);

const CITIES = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Peshawar", "Faisalabad", "Multan", "Quetta"];
const STEPS = ["You", "Topics", "Headlines", "Finish"];

export default function Onboarding() {
  const router = useRouter();
  const api = useApi();
  const { ready, signedIn } = useSession();
  const root = useRef<HTMLDivElement>(null);

  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [city, setCity] = useState("Lahore");
  const [minutes, setMinutes] = useState(10);
  const [regionMix, setRegionMix] = useState(0.5);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [picked, setPicked] = useState<string[]>([]);
  const [entities, setEntities] = useState<string[]>([]);
  const [entityDraft, setEntityDraft] = useState("");
  const [headlines, setHeadlines] = useState<Headline[]>([]);
  const [swipes, setSwipes] = useState<{ article_id: number; liked: boolean }[]>([]);
  const [about, setAbout] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (ready && !signedIn) router.replace("/");
  }, [ready, signedIn, router]);

  useEffect(() => {
    request<Topic[]>("/api/topics").then(setTopics).catch(() => {});
    request<Headline[]>("/api/onboarding/headlines").then(setHeadlines).catch(() => {});
  }, []);

  useEffect(() => {
    if (!ready || !signedIn) return;
    api.get<Me>("/api/me").then((me) => me.user.name && me.user.name !== "Guest" && me.user.name !== "Reader" && setName(me.user.name)).catch(() => {});
  }, [ready, signedIn, api]);

  useGSAP(() => {
    gsap.from(".step-body > *", { x: 40, opacity: 0, stagger: 0.06, duration: 0.5, ease: "power3.out" });
    gsap.to(".progress-fill", { width: `${((step + 1) / STEPS.length) * 100}%`, duration: 0.6, ease: "power2.out" });
  }, { scope: root, dependencies: [step] });

  useGSAP(() => {
    if (step === 1 && topics.length) gsap.from(".topic-chip", { scale: 0.8, opacity: 0, stagger: 0.025, duration: 0.35, ease: "back.out(2)" });
  }, { scope: root, dependencies: [step, topics.length] });

  const card = headlines[swipes.length];

  function swipe(liked: boolean) {
    if (!card) return;
    gsap.to(".swipe-card", {
      x: liked ? 520 : -520, rotate: liked ? 18 : -18, opacity: 0, duration: 0.4, ease: "power2.in",
      onComplete: () => {
        setSwipes((s) => [...s, { article_id: card.id, liked }]);
        gsap.set(".swipe-card", { x: 0, rotate: 0, opacity: 1 });
        gsap.from(".swipe-card", { scale: 0.92, opacity: 0, duration: 0.3 });
      },
    });
  }

  function addEntity() {
    const v = entityDraft.trim();
    if (v && !entities.includes(v)) setEntities([...entities, v]);
    setEntityDraft("");
  }

  async function finish() {
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/onboarding", {
        name: name.trim() || "Reader", city, reading_minutes: minutes, region_mix: regionMix,
        topics: picked, entities, about: about.trim() || null, swipes,
      });
      router.push("/paper?fresh=1");
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  const canNext = [name.trim().length > 0, picked.length >= 3, true, true][step];
  const groups = Array.from(new Set(topics.map((t) => t.group)));

  return (
    <div ref={root} className="min-h-screen bg-newsprint">
      <header className="mx-auto flex max-w-[760px] items-center justify-between px-4 pt-6">
        <Logo size={30} />
        <span className="caption text-ink-48">Step {step + 1} of {STEPS.length} · {STEPS[step]}</span>
      </header>
      <div className="mx-auto mt-4 h-1 max-w-[760px] overflow-hidden rounded-full bg-rule/60 px-0">
        <div className="progress-fill h-full w-0 rounded-full bg-ink" />
      </div>

      <main className="step-body mx-auto max-w-[760px] px-4 py-10">
        {step === 0 && (
          <>
            <h1 className="font-masthead text-[40px] font-bold leading-tight">Good morning. Who&apos;s reading?</h1>
            <p className="mt-2 text-ink-60">So your paper greets you, knows your weather and fits your morning.</p>
            <div className="mt-8 space-y-6">
              <div>
                <label className="label" htmlFor="name">Your name</label>
                <input id="name" className="input mt-2" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Tehman" autoFocus />
              </div>
              <div>
                <label className="label">City (weather &amp; air quality)</label>
                <div className="mt-2 flex flex-wrap gap-2">
                  {CITIES.map((c) => <button key={c} className="chip" data-on={city === c} onClick={() => setCity(c)}>{c}</button>)}
                  <input className="input !w-44 !py-2" placeholder="Other city…" onBlur={(e) => e.target.value && setCity(e.target.value)} />
                </div>
              </div>
              <div>
                <label className="label">Reading time each morning</label>
                <div className="mt-2 flex gap-2">
                  {[5, 10, 20].map((m) => <button key={m} className="chip" data-on={minutes === m} onClick={() => setMinutes(m)}>{m} min</button>)}
                </div>
              </div>
              <div>
                <label className="label" htmlFor="mix">News mix</label>
                <div className="mt-3 flex items-center gap-4 text-[14px]">
                  <span>World</span>
                  <input id="mix" type="range" min={0} max={1} step={0.1} value={regionMix} onChange={(e) => setRegionMix(Number(e.target.value))} className="flex-1 accent-[#2b241e]" />
                  <span>Pakistan</span>
                </div>
              </div>
            </div>
          </>
        )}

        {step === 1 && (
          <>
            <h1 className="font-masthead text-[40px] font-bold leading-tight">What do you care about?</h1>
            <p className="mt-2 text-ink-60">Pick at least three. You can follow specific people, teams or companies too.</p>
            <div className="mt-8 space-y-6">
              {groups.map((g) => (
                <div key={g}>
                  <div className="label">{g}</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {topics.filter((t) => t.group === g).map((t) => (
                      <button key={t.slug} className="topic-chip chip" data-on={picked.includes(t.slug)}
                        onClick={() => setPicked((p) => (p.includes(t.slug) ? p.filter((x) => x !== t.slug) : [...p, t.slug]))}>
                        {picked.includes(t.slug) ? "✓ " : ""}{t.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
              <div>
                <label className="label" htmlFor="follow">Follow names (optional)</label>
                <div className="mt-2 flex gap-2">
                  <input id="follow" className="input" value={entityDraft} onChange={(e) => setEntityDraft(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addEntity())} placeholder="e.g. Babar Azam, OpenAI, Max Verstappen" />
                  <button className="btn btn-light" onClick={addEntity}>Add</button>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {entities.map((e) => (
                    <button key={e} className="chip" data-on="true" onClick={() => setEntities(entities.filter((x) => x !== e))}>{e} ✕</button>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <h1 className="font-masthead text-[40px] font-bold leading-tight">Today&apos;s real headlines.</h1>
            <p className="mt-2 text-ink-60">Would you read it? This teaches your paper your taste — beyond topics.</p>
            <div className="mt-8 flex flex-col items-center">
              {card ? (
                <>
                  <div className="swipe-card w-full max-w-[460px] overflow-hidden rounded-[18px] bg-canvas shadow-[0_20px_50px_-20px_rgba(0,0,0,.35)]">
                    {card.image_url && <img src={card.image_url} alt="" className="h-52 w-full object-cover" />}
                    <div className="p-5">
                      <p className="kicker text-sun-deep">{card.source}</p>
                      <h2 className="headline mt-2 text-[24px]">{card.title}</h2>
                    </div>
                  </div>
                  <div className="mt-6 flex gap-4">
                    <button className="btn btn-light !px-8" onClick={() => swipe(false)}>✕ Not for me</button>
                    <button className="btn btn-dark !px-8" onClick={() => swipe(true)}>♥ I&apos;d read this</button>
                  </div>
                  <p className="mt-3 caption text-ink-48">{swipes.length + 1} / {headlines.length}</p>
                </>
              ) : (
                <div className="card w-full max-w-[460px] text-center">
                  <p className="text-[19px] font-semibold">{headlines.length ? "Nice — got your taste." : "No headlines to swipe right now."}</p>
                  <p className="mt-1 caption text-ink-48">{swipes.filter((s) => s.liked).length} liked · {swipes.filter((s) => !s.liked).length} passed</p>
                </div>
              )}
            </div>
          </>
        )}

        {step === 3 && (
          <>
            <h1 className="font-masthead text-[40px] font-bold leading-tight">Anything else?</h1>
            <p className="mt-2 text-ink-60">Optional. One sentence about you — our editor turns it into things to follow.</p>
            <textarea className="input mt-6 min-h-[110px]" value={about} onChange={(e) => setAbout(e.target.value)}
              placeholder="e.g. CS student in Lahore, building a startup, never miss a Pakistan match or an F1 race." />
            <div className="card mt-8">
              <p className="label">Your paper, so far</p>
              <p className="mt-2 font-masthead text-[22px] font-bold">{name || "Reader"}&apos;s ParhLo · {city}</p>
              <p className="mt-1 caption text-ink-60">{minutes}-minute read · {Math.round(regionMix * 100)}% Pakistan</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {picked.map((p) => <span key={p} className="rounded-full bg-newsprint px-2.5 py-1 text-[12px] font-semibold">{topics.find((t) => t.slug === p)?.label}</span>)}
                {entities.map((e) => <span key={e} className="rounded-full bg-ink px-2.5 py-1 text-[12px] font-semibold text-white">{e}</span>)}
              </div>
            </div>
            <div className="mt-4"><ErrorNote error={error} /></div>
          </>
        )}

        <div className="mt-10 flex items-center justify-between">
          <button className="btn btn-ghost" onClick={() => setStep((s) => s - 1)} disabled={step === 0 || busy}>← Back</button>
          {step < STEPS.length - 1 ? (
            <button className="btn btn-dark !px-8" disabled={!canNext} onClick={() => setStep((s) => s + 1)}>
              {step === 2 && card ? "Skip" : "Continue"}
            </button>
          ) : (
            <button className="btn btn-primary !px-8" disabled={busy} onClick={finish}>
              {busy ? <Spinner dark label="Saving your interests…" /> : "Print my paper →"}
            </button>
          )}
        </div>
      </main>
    </div>
  );
}
