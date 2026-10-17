"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import type { Edition, Morning, QuizQuestion, Story } from "@/lib/api";
import { useTracker } from "@/lib/tracker";
import { formatDate } from "../ui";
import { StoryCard } from "./StoryCard";

gsap.registerPlugin(ScrollTrigger, useGSAP);

export function PaperView({ edition, actions }: { edition: Edition; actions?: React.ReactNode }) {
  const root = useRef<HTMLDivElement>(null);
  const tracker = useTracker(edition.id);
  const byId = useMemo(() => new Map(edition.stories.map((s) => [s.id, s])), [edition]);
  const lead = byId.get(edition.lead_id) ?? edition.stories[0];

  useGSAP(() => {
    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
    tl.from(".mast-title", { y: -30, opacity: 0, duration: 0.9 })
      .from(".mast-rule", { scaleX: 0, transformOrigin: "center", duration: 0.8 }, "-=0.5")
      .from(".mast-meta > *", { opacity: 0, y: -6, stagger: 0.05, duration: 0.4 }, "-=0.5")
      .from(".front > *", { opacity: 0, y: 30, stagger: 0.1, duration: 0.7 }, "-=0.3");
    ScrollTrigger.batch(".section-block .story-card", {
      start: "top 88%",
      onEnter: (els) => gsap.from(els, { opacity: 0, y: 30, stagger: 0.08, duration: 0.6, ease: "power3.out" }),
      once: true,
    });
    gsap.from(".end-card", { scale: 0.94, opacity: 0, duration: 0.7, scrollTrigger: { trigger: ".end-card", start: "top 85%" } });
  }, { scope: root, dependencies: [edition.id] });

  return (
    <div ref={root} className="paper min-h-screen pb-28">
      <div className="mx-auto max-w-[1180px] px-4 sm:px-8">
        {/* Masthead */}
        <div className="mast-meta flex flex-wrap items-end justify-between gap-2 border-b border-ink pb-2 pt-6 text-[12px] text-ink-60">
          <span>No. {edition.number} · {edition.reader.city}</span>
          <span className="font-semibold text-ink">{formatDate(edition.edition_date)}</span>
          <WeatherLine morning={edition.morning} />
        </div>
        <h1 className="mast-title py-4 text-center font-masthead text-[56px] font-black leading-none tracking-tight sm:text-[92px]">
          Parh<span className="italic text-sun-deep">Lo</span>
        </h1>
        <p className="-mt-2 pb-3 text-center font-serif text-[14px] italic text-ink-60">The personal morning paper of {edition.reader.name}</p>
        <div className="mast-rule double-rule" />

        <div className="front">
          {/* Editor's note + morning box */}
          <div className="grid gap-6 border-b border-rule py-6 md:grid-cols-[1.4fr_1fr]">
            <div>
              <p className="kicker text-ink-48">From the editor</p>
              <p className="mt-2 font-serif text-[19px] italic leading-relaxed text-ink-80">{edition.editor_note}</p>
            </div>
            <MorningBox morning={edition.morning} />
          </div>

          {/* Front page */}
          <div className="grid gap-8 py-8 lg:grid-cols-[1.75fr_1fr]">
            {lead && <StoryCard story={lead} variant="lead" tracker={tracker} />}
            <aside className="space-y-6 lg:border-l lg:border-rule lg:pl-8">
              <div className="rounded-[4px] bg-ink p-5 text-white">
                <p className="kicker text-sun">3 things to remember today</p>
                <ol className="mt-3 space-y-3">
                  {edition.three_things.map((t, i) => (
                    <li key={i} className="flex gap-3 font-serif text-[16px] leading-snug text-white/90">
                      <span className="font-masthead text-[26px] font-bold leading-none text-sun">{i + 1}</span>{t.text}
                    </li>
                  ))}
                </ol>
              </div>
              <div>
                <p className="kicker text-ink-48">In this edition</p>
                <ul className="mt-2 space-y-1.5">
                  {edition.sections.map((s) => (
                    <li key={s.name}><a href={`#sec-${slug(s.name)}`} className="flex justify-between font-serif text-[16px] hover:text-primary">
                      <span>{s.name}</span><span className="text-ink-48">{s.story_ids.filter((id) => id !== lead?.id).length}</span></a></li>
                  ))}
                </ul>
              </div>
              {edition.morning.cricket && (
                <div className="border-t border-rule pt-4">
                  <p className="kicker text-ink-48">Cricket</p>
                  <a href={edition.morning.cricket.url} target="_blank" rel="noopener noreferrer" className="headline mt-1 block text-[18px] hover:underline">{edition.morning.cricket.title}</a>
                  <p className="mt-1 text-[12px] text-ink-48">{edition.morning.cricket.source}</p>
                </div>
              )}
            </aside>
          </div>
        </div>

        {/* Sections */}
        {edition.sections.map((sec) => {
          const stories = sec.story_ids.filter((id) => id !== lead?.id).map((id) => byId.get(id)).filter(Boolean) as Story[];
          if (!stories.length) return null;
          return (
            <section key={sec.name} id={`sec-${slug(sec.name)}`} className="section-block scroll-mt-20 pt-6">
              <div className="flex items-center gap-4 border-t-[3px] border-ink pt-2">
                <h2 className="font-masthead text-[26px] font-bold">{sec.name}</h2>
                <span className="caption text-ink-48">{stories.length} {stories.length === 1 ? "story" : "stories"}</span>
              </div>
              <div className="mt-3 grid gap-x-8 gap-y-6 md:grid-cols-2 lg:grid-cols-3">
                {stories.map((s) => <StoryCard key={s.id} story={s} tracker={tracker} />)}
              </div>
            </section>
          );
        })}

        {/* The end */}
        <div className="end-card mx-auto mt-16 max-w-[640px] rounded-[18px] border border-rule bg-white/60 p-8 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-ink text-[26px] text-sun">✓</div>
          <h2 className="mt-4 font-masthead text-[32px] font-bold">You&apos;re done for today.</h2>
          <p className="mt-2 text-ink-60">That&apos;s everything that matters to you this morning. See you tomorrow.</p>
          {edition.recall_quiz.length > 0 && <RecallQuiz quiz={edition.recall_quiz} onAnswer={(ok, id) => tracker.track(ok ? "quiz_correct" : "quiz_wrong", id)} />}
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            {actions}
            <Link href="/profile" className="btn btn-light">See what your paper learned</Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function WeatherLine({ morning }: { morning: Morning }) {
  const w = morning.weather;
  const a = morning.air;
  return (
    <span>
      {w ? `${w.temp}°C ${w.condition}` : ""}
      {a?.aqi != null && <span className={a.level >= 3 ? "ml-2 font-semibold text-danger" : "ml-2"}>· AQI {a.aqi}{a.level >= 3 ? " ⚠" : ""}</span>}
    </span>
  );
}

export function MorningBox({ morning }: { morning: Morning }) {
  const w = morning.weather, a = morning.air, r = morning.rates?.pkr;
  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-[4px] border border-rule bg-rule text-[14px]">
      <div className="bg-newsprint p-3">
        <p className="kicker text-ink-48">{morning.city} today</p>
        {w ? <p className="mt-1"><span className="font-masthead text-[30px] font-bold">{w.temp}°</span> <span className="text-ink-60">{w.condition}</span></p> : <p className="mt-1 text-ink-48">—</p>}
        {w && <p className="text-[12px] text-ink-48">H {w.high}° · L {w.low}° · Rain {w.rain_chance}%</p>}
      </div>
      <div className={`p-3 ${morning.smog_alert ? "bg-[#fbe9e7]" : "bg-newsprint"}`}>
        <p className={`kicker ${morning.smog_alert ? "text-danger" : "text-ink-48"}`}>{morning.smog_alert ? "⚠ Smog alert" : "Air quality"}</p>
        {a?.aqi != null ? <p className="mt-1"><span className="font-masthead text-[30px] font-bold">{a.aqi}</span> <span className="text-ink-60">{a.label}</span></p> : <p className="mt-1 text-ink-48">—</p>}
        {a?.advice && <p className="text-[12px] text-ink-60">{a.advice}</p>}
      </div>
      <div className="col-span-2 bg-newsprint p-3">
        <p className="kicker text-ink-48">Rupee today</p>
        {r ? (
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
            {Object.entries(r).map(([cur, v]) => <span key={cur}><span className="text-ink-48">{cur}</span> <span className="font-semibold">Rs {v.toFixed(2)}</span></span>)}
          </div>
        ) : <p className="mt-1 text-ink-48">—</p>}
      </div>
    </div>
  );
}

function RecallQuiz({ quiz, onAnswer }: { quiz: QuizQuestion[]; onAnswer: (correct: boolean, storyId: number) => void }) {
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const score = Object.entries(answers).filter(([i, a]) => quiz[Number(i)].answer === a).length;
  return (
    <div className="mt-8 text-left">
      <p className="kicker text-sun-deep">Yesterday&apos;s 3 things — do you remember?</p>
      {quiz.map((q, i) => (
        <div key={i} className="mt-4">
          <p className="font-serif text-[17px] font-semibold">{q.question}</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {q.options.map((opt, j) => {
              const picked = answers[i] === j, done = answers[i] !== undefined, correct = q.answer === j;
              return (
                <button key={j} disabled={done}
                  onClick={() => { setAnswers((a) => ({ ...a, [i]: j })); onAnswer(correct, q.story_id); }}
                  className={`rounded-[11px] border px-3 py-2 text-left text-[14px] transition-colors ${done && correct ? "border-success bg-[#e9f6ec]" : picked ? "border-danger bg-[#fff1f0]" : "border-rule bg-white hover:border-ink"}`}>
                  {opt}
                </button>
              );
            })}
          </div>
        </div>
      ))}
      {Object.keys(answers).length === quiz.length && (
        <p className="mt-4 text-center font-masthead text-[22px] font-bold">{score} / {quiz.length} remembered {score === quiz.length ? "🏆" : ""}</p>
      )}
    </div>
  );
}

const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-");
