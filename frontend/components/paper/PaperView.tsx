"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import type { Edition, Morning, QuizQuestion, Story } from "@/lib/api";
import { useTracker } from "@/lib/tracker";
import { formatDate } from "../ui";
import { StoryCard, type StoryState } from "./StoryCard";

gsap.registerPlugin(ScrollTrigger, useGSAP);

export function PaperView({ edition, actions }: { edition: Edition; actions?: React.ReactNode }) {
  const root = useRef<HTMLDivElement>(null);
  const tracker = useTracker(edition.id);
  const byId = useMemo(() => new Map(edition.stories.map((s) => [s.id, s])), [edition]);
  const lead = byId.get(edition.lead_id) ?? edition.stories[0];
  const initial = (id: number): StoryState => ({
    reaction: edition.state?.reactions[String(id)] ?? null, saved: edition.state?.saved.includes(id) ?? false,
  });

  useGSAP(() => {
    gsap.timeline({ defaults: { ease: "power3.out" } })
      .from(".mast-meta", { opacity: 0, duration: 0.5 })
      .from(".mast-title", { y: 24, opacity: 0, duration: 0.8 }, "-=0.3")
      .from(".mast-rule", { scaleX: 0, transformOrigin: "center", duration: 0.8 }, "-=0.5")
      .from(".today-card", { y: 20, opacity: 0, stagger: 0.07, duration: 0.5 }, "-=0.4")
      .from(".front > *", { y: 30, opacity: 0, stagger: 0.12, duration: 0.7 }, "-=0.3");
    ScrollTrigger.batch(".section-block .story-card", {
      start: "top 90%", once: true,
      onEnter: (els) => gsap.from(els, { y: 30, opacity: 0, stagger: 0.08, duration: 0.6, ease: "power3.out" }),
    });
    gsap.from(".end-card > *", { y: 20, opacity: 0, stagger: 0.08, duration: 0.6, scrollTrigger: { trigger: ".end-card", start: "top 85%" } });
  }, { scope: root, dependencies: [edition.id] });

  return (
    <div ref={root} className="paper min-h-screen pb-24">
      <div className="mx-auto max-w-[1080px] px-4 sm:px-6">
        {/* Masthead */}
        <div className="mast-meta flex flex-wrap items-center justify-between gap-2 border-b border-hairline pb-3 pt-6 t-caption text-ink-60">
          <span>No. {edition.number}</span>
          <span className="text-ink">{formatDate(edition.edition_date)}</span>
          <span>{edition.reader.city}</span>
        </div>
        <h1 className="mast-title masthead py-5 text-center text-[56px] sm:text-[88px]">ParhLo</h1>
        <p className="-mt-2 pb-4 text-center t-caption text-ink-60">For {edition.reader.name}</p>
        <div className="mast-rule double-rule" />

        {/* Today */}
        <TodayCards morning={edition.morning} />

        {/* Editor's note */}
        {edition.editor_note && (
          <div className="mx-auto max-w-[760px] pt-8 text-center">
            <p className="t-caption font-semibold text-ink-60">Today in brief</p>
            <p className="mt-2 font-serif text-[19px] leading-relaxed text-ink-80">{edition.editor_note}</p>
          </div>
        )}

        {/* Front page */}
        <div className="front grid gap-10 border-b border-hairline py-10 lg:grid-cols-[1.7fr_1fr]">
          {lead && <StoryCard story={lead} variant="lead" tracker={tracker} initial={initial(lead.id)} />}
          <aside className="space-y-8">
            <div className="rounded-[18px] bg-tile p-6 text-white">
              <p className="t-caption font-semibold text-primary-on-dark">3 things to remember</p>
              <ol className="mt-4 space-y-4">
                {edition.three_things.map((t, i) => (
                  <li key={i} className="flex gap-3 t-body leading-snug text-white/90">
                    <span className="text-[22px] font-semibold leading-none text-primary-on-dark">{i + 1}</span>{t.text}
                  </li>
                ))}
              </ol>
            </div>
            <div>
              <p className="t-caption font-semibold text-ink-60">In this paper</p>
              <ul className="mt-3 divide-y divide-hairline">
                {edition.sections.map((s) => {
                  const n = s.story_ids.filter((id) => id !== lead?.id).length;
                  return n ? (
                    <li key={s.name}><a href={`#sec-${slug(s.name)}`} className="flex justify-between py-2.5 t-body hover:text-primary">
                      <span>{s.name}</span><span className="text-ink-48">{n}</span></a></li>
                  ) : null;
                })}
              </ul>
            </div>
          </aside>
        </div>

        {/* Sections */}
        {edition.sections.map((sec) => {
          const stories = sec.story_ids.filter((id) => id !== lead?.id).map((id) => byId.get(id)).filter(Boolean) as Story[];
          if (!stories.length) return null;
          return (
            <section key={sec.name} id={`sec-${slug(sec.name)}`} className="section-block scroll-mt-16 pt-12">
              <h2 className="t-section">{sec.name}</h2>
              <div className="mt-2 grid gap-x-8 gap-y-8 md:grid-cols-2 lg:grid-cols-3">
                {stories.map((s) => <StoryCard key={s.id} story={s} tracker={tracker} initial={initial(s.id)} />)}
              </div>
            </section>
          );
        })}

        {/* End */}
        <div className="end-card mx-auto mt-20 max-w-[640px] rounded-[18px] bg-parchment p-10 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary text-[22px] text-white">✓</div>
          <h2 className="t-section mt-5">That&apos;s today&apos;s paper.</h2>
          <p className="t-body mt-2 text-ink-60">Your next paper will be ready tomorrow morning.</p>
          {edition.recall_quiz.length > 0 && <RecallQuiz quiz={edition.recall_quiz} onAnswer={(ok, id) => tracker.track(ok ? "quiz_correct" : "quiz_wrong", id)} />}
          <div className="mt-8 flex flex-wrap justify-center gap-3">{actions}</div>
          <Link href="/dashboard#memory" className="link mt-5 inline-block t-body">See what changed in your interests ›</Link>
        </div>
      </div>
    </div>
  );
}

function TodayCards({ morning }: { morning: Morning }) {
  const w = morning.weather, a = morning.air, r = morning.rates?.pkr;
  const cards = [
    { k: morning.city, v: w ? `${w.temp}°` : "—", s: w ? `${w.condition} · H ${w.high}° L ${w.low}°` : "" },
    { k: morning.smog_alert ? "Air quality · Alert" : "Air quality", v: a?.aqi != null ? String(a.aqi) : "—", s: a?.advice ?? a?.label ?? "", alert: morning.smog_alert },
    { k: "US dollar", v: r ? `Rs ${r.USD.toFixed(0)}` : "—", s: r ? `€ Rs ${r.EUR.toFixed(0)} · £ Rs ${r.GBP.toFixed(0)}` : "" },
    { k: "Cricket", v: morning.cricket ? "Latest" : "—", s: morning.cricket?.title ?? "No match news today", href: morning.cricket?.url },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 pt-6 md:grid-cols-4">
      {cards.map((c) => {
        const body = (
          <>
            <p className={`t-caption ${c.alert ? "font-semibold text-danger" : "text-ink-60"}`}>{c.k}</p>
            <p className="mt-1 text-[24px] font-semibold tracking-tight">{c.v}</p>
            <p className="mt-0.5 line-clamp-2 t-caption text-ink-60">{c.s}</p>
          </>
        );
        return c.href ? (
          <a key={c.k} href={c.href} target="_blank" rel="noopener noreferrer" className="today-card rounded-[18px] bg-parchment p-4 hover:bg-[#ececf0]">{body}</a>
        ) : (
          <div key={c.k} className={`today-card rounded-[18px] p-4 ${c.alert ? "bg-[#fff2f2]" : "bg-parchment"}`}>{body}</div>
        );
      })}
    </div>
  );
}

function RecallQuiz({ quiz, onAnswer }: { quiz: QuizQuestion[]; onAnswer: (correct: boolean, storyId: number) => void }) {
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const score = Object.entries(answers).filter(([i, a]) => quiz[Number(i)].answer === a).length;
  return (
    <div className="mt-8 text-left">
      <p className="t-tagline !text-[17px]">Quick quiz on yesterday&apos;s paper</p>
      {quiz.map((q, i) => (
        <div key={i} className="mt-5">
          <p className="t-body font-semibold">{q.question}</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {q.options.map((opt, j) => {
              const picked = answers[i] === j, done = answers[i] !== undefined, correct = q.answer === j;
              return (
                <button key={j} disabled={done}
                  onClick={() => { setAnswers((a) => ({ ...a, [i]: j })); onAnswer(correct, q.story_id); }}
                  className={`rounded-[12px] px-4 py-2.5 text-left t-caption transition-colors ${done && correct ? "bg-[#e9f6ec] text-success" : picked ? "bg-[#fff2f2] text-danger" : "bg-canvas hover:bg-pearl"}`}
                  style={{ boxShadow: "inset 0 0 0 1px #e0e0e0" }}>
                  {opt}
                </button>
              );
            })}
          </div>
        </div>
      ))}
      {Object.keys(answers).length === quiz.length && (
        <p className="mt-5 text-center t-tagline">{score} of {quiz.length} correct</p>
      )}
    </div>
  );
}

const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-");
