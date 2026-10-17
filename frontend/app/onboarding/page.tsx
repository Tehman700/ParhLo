"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { FrontPagePreview, type Preview } from "@/components/FrontPagePreview";
import { LogoMark } from "@/components/Logo";
import { ErrorNote, Spinner } from "@/components/ui";
import { request, type Headline, type Me, type Topic } from "@/lib/api";
import { useApi, useSession } from "@/lib/auth";

gsap.registerPlugin(useGSAP);

const CITIES = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Peshawar", "Faisalabad", "Multan", "Quetta"];
const STEPS = ["About you", "Topics", "Headlines", "Review"];

export default function Onboarding() {
  const router = useRouter();
  const api = useApi();
  const { ready, signedIn } = useSession();
  const root = useRef<HTMLDivElement>(null);

  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [city, setCity] = useState("Lahore");
  const [otherCity, setOtherCity] = useState("");
  const [minutes, setMinutes] = useState(10);
  const [regionMix, setRegionMix] = useState(0.5);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [picked, setPicked] = useState<string[]>([]);
  const [entities, setEntities] = useState<string[]>([]);
  const [entityDraft, setEntityDraft] = useState("");
  const [headlines, setHeadlines] = useState<Headline[]>([]);
  const [swipes, setSwipes] = useState<{ article_id: number; liked: boolean; topic?: string }[]>([]);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [about, setAbout] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (ready && !signedIn) router.replace("/sign-in");
  }, [ready, signedIn, router]);

  useEffect(() => {
    request<Topic[]>("/api/topics").then(setTopics).catch(() => {});
  }, []);

  // C1: live front-page preview while picking topics (debounced).
  useEffect(() => {
    if (step !== 1) return;
    const t = setTimeout(() => {
      setPreviewLoading(true);
      const q = new URLSearchParams({ topics: picked.join(","), entities: entities.join(",") });
      request<Preview>(`/api/onboarding/preview?${q}`)
        .then(setPreview).catch(() => {}).finally(() => setPreviewLoading(false));
    }, 350);
    return () => clearTimeout(t);
  }, [step, picked, entities]);

  // C2: swipe headlines from the chosen topics first, then a few to discover new interests.
  useEffect(() => {
    if (step !== 2) return;
    let cancelled = false;
    request<Headline[]>(`/api/onboarding/headlines?topics=${picked.join(",")}`)
      .then((h) => !cancelled && setHeadlines(h)).catch(() => {});
    return () => { cancelled = true; };
  }, [step, picked]);

  useEffect(() => {
    if (!ready || !signedIn) return;
    api.get<Me>("/api/me").then((me) => me.user.name && !["Guest", "Reader"].includes(me.user.name) && setName(me.user.name)).catch(() => {});
  }, [ready, signedIn, api]);

  useGSAP(() => {
    gsap.from(".step-body > *", { y: 20, opacity: 0, stagger: 0.06, duration: 0.55, ease: "power3.out" });
    gsap.to(".progress-fill", { width: `${((step + 1) / STEPS.length) * 100}%`, duration: 0.7, ease: "power2.out" });
  }, { scope: root, dependencies: [step] });

  useGSAP(() => {
    if (step === 1 && topics.length) gsap.from(".topic-chip", { y: 8, opacity: 0, stagger: 0.02, duration: 0.35, ease: "power2.out" });
  }, { scope: root, dependencies: [step, topics.length] });

  const swipedIds = new Set(swipes.map((s) => s.article_id));
  const passes: Record<string, number> = {};
  for (const sw of swipes) if (!sw.liked && sw.topic) passes[sw.topic] = (passes[sw.topic] ?? 0) + 1;
  const queue = headlines.filter((h) => !swipedIds.has(h.id) && (passes[h.topic ?? ""] ?? 0) < 2);
  const card = queue[0];

  function swipe(liked: boolean) {
    if (!card) return;
    gsap.to(".swipe-card", {
      x: liked ? 420 : -420, rotate: liked ? 10 : -10, opacity: 0, duration: 0.35, ease: "power2.in",
      onComplete: () => {
        setSwipes((s) => [...s, { article_id: card.id, liked, topic: card.topic }]);
        gsap.fromTo(".swipe-card", { x: 0, rotate: 0, opacity: 0, scale: 0.96 }, { opacity: 1, scale: 1, duration: 0.3 });
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
        name: name.trim() || "Reader", city: otherCity.trim() || city, reading_minutes: minutes, region_mix: regionMix,
        topics: picked, entities, about: about.trim() || null, swipes: swipes.map(({ article_id, liked }) => ({ article_id, liked })),
      });
      router.push("/dashboard?welcome=1"); // the first paper is built in the background there
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  const canNext = [name.trim().length > 0, picked.length >= 3, true, true][step];
  const groups = Array.from(new Set(topics.map((t) => t.group)));
  const label = (slug: string) => topics.find((t) => t.slug === slug)?.label ?? slug;

  return (
    <div ref={root} className="min-h-screen bg-canvas">
      <header className="sticky top-0 z-10 bg-canvas/90 backdrop-blur-xl">
        <div className="mx-auto flex h-11 max-w-[1024px] items-center justify-between px-4 text-[12px]">
          <Link href="/" className="flex items-center gap-1.5 text-[14px] font-semibold tracking-tight"><LogoMark size={20} />ParhLo</Link>
          <span className="text-ink-60">Step {step + 1} of {STEPS.length}</span>
        </div>
        <div className="h-[2px] w-full bg-divider"><div className="progress-fill h-full w-0 bg-primary" /></div>
      </header>

      <main className={`step-body mx-auto px-4 pb-32 pt-14 ${step === 1 ? "max-w-[1040px]" : "max-w-[640px]"}`}>
        <p className="t-caption font-semibold text-primary">{STEPS[step]}</p>

        {step === 0 && (
          <>
            <h1 className="t-display mt-2">Tell us a little about you.</h1>
            <p className="t-body mt-3 text-ink-60">We use this for your weather, and to fit your paper to your morning.</p>
            <div className="mt-10 space-y-9">
              <div>
                <label className="t-tagline !text-[17px]" htmlFor="name">Your name</label>
                <input id="name" className="input mt-3" value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" autoFocus />
              </div>
              <div>
                <p className="t-tagline !text-[17px]">City</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {CITIES.map((c) => <button key={c} className="chip" data-on={!otherCity && city === c} onClick={() => { setCity(c); setOtherCity(""); }}>{c}</button>)}
                </div>
                <input className="input mt-3" placeholder="Other city" value={otherCity} onChange={(e) => setOtherCity(e.target.value)} />
              </div>
              <div>
                <p className="t-tagline !text-[17px]">Reading time</p>
                <p className="t-caption mt-1 text-ink-60">How long do you want to spend on your paper each morning?</p>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  {[5, 10, 20].map((m) => <button key={m} className="chip !py-3" data-on={minutes === m} onClick={() => setMinutes(m)}>{m} minutes</button>)}
                </div>
              </div>
              <div>
                <p className="t-tagline !text-[17px]">News from</p>
                <div className="mt-4 flex items-center gap-4 t-caption text-ink-60">
                  <span>Mostly world</span>
                  <input type="range" min={0} max={1} step={0.1} value={regionMix} aria-label="Pakistan and world news mix"
                    onChange={(e) => setRegionMix(Number(e.target.value))} className="flex-1 accent-[#0066cc]" />
                  <span>Mostly Pakistan</span>
                </div>
              </div>
            </div>
          </>
        )}

        {step === 1 && (
          <div className="grid gap-10 lg:grid-cols-[1fr_340px]">
          <div>
            <h1 className="t-display mt-2">Choose your topics.</h1>
            <p className="t-body mt-3 text-ink-60">Pick at least three. Your front page updates as you choose.</p>
            <div className="mt-10 space-y-8">
              {groups.map((g) => (
                <div key={g}>
                  <p className="t-caption font-semibold text-ink-60">{g}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {topics.filter((t) => t.group === g).map((t) => (
                      <button key={t.slug} className="topic-chip chip" data-on={picked.includes(t.slug)}
                        onClick={() => setPicked((p) => (p.includes(t.slug) ? p.filter((x) => x !== t.slug) : [...p, t.slug]))}>
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
              <div>
                <label className="t-tagline !text-[17px]" htmlFor="follow">Follow people, teams or companies</label>
                <p className="t-caption mt-1 text-ink-60">Optional. For example: Babar Azam, OpenAI, Max Verstappen.</p>
                <div className="mt-3 flex gap-2">
                  <input id="follow" className="input" value={entityDraft} onChange={(e) => setEntityDraft(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addEntity())} placeholder="Add a name" />
                  <button className="btn btn-light !h-12 shrink-0" onClick={addEntity} disabled={!entityDraft.trim()}>Add</button>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {entities.map((e) => (
                    <button key={e} className="chip" data-on="true" onClick={() => setEntities(entities.filter((x) => x !== e))} aria-label={`Remove ${e}`}>
                      {e} <span className="text-ink-48">✕</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <aside className="lg:sticky lg:top-20 lg:self-start">
            <FrontPagePreview preview={preview} name={name.trim()} loading={previewLoading} />
          </aside>
          </div>
        )}

        {step === 2 && (
          <>
            <h1 className="t-display mt-2">Would you read these?</h1>
            <p className="t-body mt-3 text-ink-60">Real headlines from today, starting with your topics. Pass on a topic twice and we&apos;ll stop showing it.</p>
            <div className="mt-10 flex flex-col items-center">
              {card ? (
                <>
                  <div className="swipe-card w-full overflow-hidden rounded-[18px] border border-hairline bg-canvas">
                    {card.image_url && <img src={card.image_url} alt="" className="h-56 w-full object-cover" />}
                    <div className="p-6">
                      <p className="t-caption text-ink-60">
                        {card.discovery ? <span className="mr-2 rounded-full bg-parchment px-2 py-0.5 t-fine font-semibold text-ink-60">Something new</span> : null}
                        {card.source}
                      </p>
                      <h2 className="mt-1 text-[24px] font-semibold leading-tight tracking-tight">{card.title}</h2>
                    </div>
                  </div>
                  <div className="mt-6 grid w-full grid-cols-2 gap-3">
                    <button className="btn btn-light !h-12" onClick={() => swipe(false)}>Not interested</button>
                    <button className="btn btn-primary !h-12" onClick={() => swipe(true)}>Interested</button>
                  </div>
                  <p className="mt-4 t-caption text-ink-48">{swipes.length + 1} of {swipes.length + queue.length}</p>
                </>
              ) : (
                <div className="w-full rounded-[18px] bg-parchment p-10 text-center">
                  <p className="t-tagline">{headlines.length ? "Thanks, that helps." : "No headlines right now."}</p>
                  <p className="mt-1 t-caption text-ink-60">
                    {headlines.length ? `${swipes.filter((s) => s.liked).length} interested, ${swipes.filter((s) => !s.liked).length} not interested.` : "You can skip this step."}
                  </p>
                </div>
              )}
            </div>
          </>
        )}

        {step === 3 && (
          <>
            <h1 className="t-display mt-2">Anything else we should know?</h1>
            <p className="t-body mt-3 text-ink-60">Optional. Describe what you do or follow, in a sentence or two.</p>
            <textarea className="input mt-8 min-h-[120px]" value={about} onChange={(e) => setAbout(e.target.value)}
              placeholder="For example: I study computer science in Lahore and follow startups, cricket and Formula 1." />
            <div className="mt-10 rounded-[18px] bg-parchment p-6">
              <p className="t-caption font-semibold text-ink-60">Your paper</p>
              <dl className="mt-4 space-y-3 t-body">
                <div className="flex justify-between gap-4"><dt className="text-ink-60">Name</dt><dd>{name || "—"}</dd></div>
                <div className="flex justify-between gap-4"><dt className="text-ink-60">City</dt><dd>{otherCity || city}</dd></div>
                <div className="flex justify-between gap-4"><dt className="text-ink-60">Reading time</dt><dd>{minutes} minutes</dd></div>
                <div className="flex justify-between gap-4"><dt className="text-ink-60">Topics</dt><dd className="text-right">{picked.map(label).join(", ")}</dd></div>
                {entities.length > 0 && <div className="flex justify-between gap-4"><dt className="text-ink-60">Following</dt><dd className="text-right">{entities.join(", ")}</dd></div>}
              </dl>
            </div>
            <div className="mt-4 flex gap-3 rounded-[18px] border border-hairline p-5">
              <span className="text-[20px] leading-none text-primary">ⓘ</span>
              <p className="t-caption text-ink-60">
                Your paper always includes the day&apos;s two biggest stories, plus what you care about. You can see and change
                everything ParhLo learns about you on the Interests page.
              </p>
            </div>
            <div className="mt-4"><ErrorNote error={error} /></div>
          </>
        )}
      </main>

      <footer className="fixed inset-x-0 bottom-0 border-t border-hairline bg-canvas/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[640px] items-center justify-between px-4 py-4">
          <button className="link t-body disabled:opacity-0" onClick={() => setStep((s) => s - 1)} disabled={step === 0 || busy}>Back</button>
          {step < STEPS.length - 1 ? (
            <button className="btn btn-primary" disabled={!canNext} onClick={() => setStep((s) => s + 1)}>
              {step === 2 && card ? "Skip" : "Continue"}
            </button>
          ) : (
            <button className="btn btn-primary" disabled={busy} onClick={finish}>
              {busy ? <Spinner dark label="Saving" /> : "Create my paper"}
            </button>
          )}
        </div>
      </footer>
    </div>
  );
}
