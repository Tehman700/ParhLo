"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Link from "next/link";
import { useRef } from "react";
import { LogoMark } from "./Logo";
import { TopBar } from "./ui";

gsap.registerPlugin(ScrollTrigger, useGSAP);

/* Every number here is measured in production (docs/architecture.md §8). */
const USES = [
  { kind: "Choice", title: "Which topic is this?", body: "Jev picks one of 17 topics for every article, with a probability for each. That is how a story lands in your Cricket or Economy section.", detail: "17 topics · 1 call per article" },
  { kind: "Yes / no", title: "Is this real news?", body: "Quizzes, podcast listings, tag pages and promotions are flagged and kept out of your paper.", detail: "Hidden when 78% sure it isn't news" },
  { kind: "Score", title: "How important is it?", body: "Every story is rated on five levels, from filler to top national news. The two biggest stories of the day go to every reader.", detail: "5 levels · 2 Top story slots" },
  { kind: "Yes / no", title: "Is the summary faithful?", body: "After a summary is written, Jev reads it next to the original article and looks for any claim, number, name or date the article doesn't support.", detail: "✓ only when under 30% risk" },
  { kind: "Choice", title: "Which story is your question about?", body: "When you ask your paper something, Jev decides which of today's stories it's about, so the answer comes from the right articles.", detail: "Routes every question" },
];

const NUMBERS = [
  { v: 94, suffix: "%", label: "of summaries judged correctly in our test of real and deliberately falsified summaries. The same accuracy as the language model it replaced." },
  { v: 434, suffix: " ms", label: "median time to check a summary, against 941 ms for the language model. About two to three times faster." },
  { v: 1029, suffix: "", label: "articles sorted, filtered and scored in 30 seconds in one nightly run. 139 of them were flagged as not real news." },
];

export function JevExplainer() {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    gsap.timeline({ defaults: { ease: "power3.out" } })
      .from(".jx-logos > *", { y: 16, opacity: 0, stagger: 0.12, duration: 0.6 })
      .from(".jx-hero-text > *", { y: 20, opacity: 0, stagger: 0.08, duration: 0.6 }, "-=0.3");

    // The decision demo plays when it scrolls into view (and again with "Replay").
    const demo = gsap.timeline({ paused: true, defaults: { ease: "power3.out" } })
      .from(".jx-article", { x: -60, opacity: 0, duration: 0.6 })
      .from(".jx-q", { x: 60, opacity: 0, stagger: 0.35, duration: 0.5 }, "-=0.2")
      .from(".jx-bar", { width: 0, stagger: 0.35, duration: 0.8, ease: "power2.out" }, "<0.1")
      .from(".jx-dot", { scale: 0, stagger: 0.06, duration: 0.25, ease: "back.out(3)" }, "-=0.6")
      .from(".jx-check", { y: 30, opacity: 0, duration: 0.6 }, "+=0.2")
      .from(".jx-risk", { width: 0, duration: 0.8, ease: "power2.out" }, "-=0.2")
      .from(".jx-verdict", { scale: 0.6, opacity: 0, duration: 0.45, ease: "back.out(2.4)" });
    ScrollTrigger.create({ trigger: ".jx-demo", start: "top 70%", once: true, onEnter: () => demo.play() });
    root.current?.querySelector(".jx-replay")?.addEventListener("click", () => demo.restart());

    gsap.utils.toArray<HTMLElement>(".jx-card").forEach((el, k) => {
      gsap.from(el, { x: k % 2 ? 60 : -60, opacity: 0, duration: 0.7, ease: "power3.out", scrollTrigger: { trigger: el, start: "top 85%" } });
    });
    gsap.utils.toArray<HTMLElement>(".jx-count").forEach((el) => {
      const o = { v: 0 }, to = Number(el.dataset.value);
      gsap.to(o, { v: to, duration: 1.5, ease: "power2.out", scrollTrigger: { trigger: el, start: "top 85%" },
        onUpdate: () => (el.textContent = Math.round(o.v).toLocaleString("en-US")) });
    });
    gsap.from(".jx-split > *", { y: 30, opacity: 0, stagger: 0.12, duration: 0.7, scrollTrigger: { trigger: ".jx-split", start: "top 80%" } });
  }, { scope: root });

  return (
    <div ref={root} className="overflow-x-hidden">
      <TopBar />

      {/* Hero */}
      <section className="bg-parchment px-4 pb-20 pt-16 text-center sm:pt-24">
        <div className="jx-logos flex items-center justify-center gap-4">
          <LogoMark size={64} />
          <span className="text-[28px] font-light text-ink-48">×</span>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/brand/typesafe-jev.png" alt="TypeSafe" width={64} height={64} className="h-16 w-16 rounded-full" />
        </div>
        <div className="jx-hero-text">
          <p className="mt-8 t-tagline text-ink-60">Powered by Jev from TypeSafe</p>
          <h1 className="t-hero mx-auto mt-2 max-w-3xl">How ParhLo checks every story.</h1>
          <p className="t-lead mx-auto mt-4 max-w-2xl text-ink-60">
            Jev is a decision model. It doesn&apos;t write anything. It answers precise questions about each article, with a probability for every answer. The language model writes your paper; Jev decides what goes in it and checks what it says.
          </p>
        </div>
      </section>

      {/* Demo */}
      <section className="jx-demo bg-canvas px-4 py-20 sm:py-28">
        <div className="mx-auto max-w-[1000px]">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h2 className="t-display">One article, four decisions.</h2>
            <button className="jx-replay link t-body">Replay ↻</button>
          </div>
          <p className="mt-2 t-caption text-ink-48">An illustrative example of what Jev answers for every article.</p>
          <div className="mt-10 grid items-start gap-6 md:grid-cols-[1fr_1.15fr]">
            <div className="jx-article rounded-[18px] border border-hairline p-6">
              <p className="kicker">Incoming article</p>
              <p className="headline mt-2 text-[22px]">State Bank keeps interest rate unchanged at 11pc</p>
              <p className="deck mt-2 !text-[15px]">The central bank held its policy rate for a third meeting, citing easing inflation and a stable rupee.</p>
              <p className="mt-3 t-caption text-ink-48">Business Recorder</p>
            </div>
            <div className="space-y-3">
              <div className="jx-q rounded-[18px] bg-parchment p-4">
                <div className="flex justify-between t-caption"><span className="font-semibold">Which topic?</span><span className="text-ink-48">Choice</span></div>
                <div className="mt-2 flex items-center gap-3 t-caption"><span className="w-24">Economy</span><div className="h-2 flex-1 overflow-hidden rounded-full bg-black/5"><div className="jx-bar h-full rounded-full bg-primary" style={{ width: "92%" }} /></div><span className="w-10 text-right">92%</span></div>
                <div className="mt-1.5 flex items-center gap-3 t-caption text-ink-60"><span className="w-24">Business</span><div className="h-2 flex-1 overflow-hidden rounded-full bg-black/5"><div className="jx-bar h-full rounded-full bg-primary/40" style={{ width: "6%" }} /></div><span className="w-10 text-right">6%</span></div>
              </div>
              <div className="jx-q rounded-[18px] bg-parchment p-4">
                <div className="flex justify-between t-caption"><span className="font-semibold">Is it real news?</span><span className="text-ink-48">Yes / no</span></div>
                <div className="mt-2 flex items-center gap-3 t-caption"><span className="w-24">Yes</span><div className="h-2 flex-1 overflow-hidden rounded-full bg-black/5"><div className="jx-bar h-full rounded-full bg-success" style={{ width: "97%" }} /></div><span className="w-10 text-right">97%</span></div>
              </div>
              <div className="jx-q rounded-[18px] bg-parchment p-4">
                <div className="flex justify-between t-caption"><span className="font-semibold">How important?</span><span className="text-ink-48">Score</span></div>
                <div className="mt-2 flex items-center gap-2 t-caption">
                  {[0, 1, 2, 3, 4].map((k) => <span key={k} className={`jx-dot h-3 w-8 rounded-full ${k < 4 ? "bg-primary" : "bg-black/10"}`} />)}
                  <span className="ml-2">Important: affects many people</span>
                </div>
              </div>
            </div>
          </div>
          <div className="jx-check mt-6 rounded-[18px] bg-tile p-6 text-white">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="t-caption font-semibold text-primary-on-dark">After the summary is written</p>
              <span className="t-caption text-white/50">Yes / no</span>
            </div>
            <p className="mt-2 font-serif text-[18px] leading-relaxed text-white/90">&ldquo;The State Bank kept its policy rate at 11% for a third meeting, pointing to easing inflation and a stable rupee.&rdquo;</p>
            <p className="mt-4 t-caption text-white/70">Does this summary say anything the article doesn&apos;t?</p>
            <div className="mt-2 flex items-center gap-3 t-caption">
              <span className="w-24 text-white/70">Risk</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/10"><div className="jx-risk h-full rounded-full bg-primary-on-dark" style={{ width: "4%" }} /></div>
              <span className="w-10 text-right">4%</span>
            </div>
            <p className="jx-verdict mt-4 inline-block rounded-full bg-[#e9f6ec] px-3 py-1 t-caption font-semibold text-success">✓ Checked against source · 92%</p>
          </div>
        </div>
      </section>

      {/* Where Jev works */}
      <section className="bg-parchment px-4 py-20 sm:py-28">
        <div className="mx-auto max-w-[1000px]">
          <h2 className="t-display text-center">Five places Jev works in your paper.</h2>
          <div className="mt-12 grid gap-5 md:grid-cols-2">
            {USES.map((u, k) => (
              <div key={u.title} className={`jx-card rounded-[18px] bg-canvas p-7 ${k === USES.length - 1 ? "md:col-span-2" : ""}`}>
                <div className="flex items-center justify-between gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-[15px] font-semibold text-white">{k + 1}</span>
                  <span className="rounded-full bg-parchment px-3 py-1 t-fine font-semibold text-ink-60">{u.kind}</span>
                </div>
                <h3 className="mt-4 t-tagline">{u.title}</h3>
                <p className="mt-2 t-body text-ink-60">{u.body}</p>
                <p className="mt-4 t-caption font-semibold text-primary">{u.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Numbers */}
      <section className="tile-dark px-4 py-20 sm:py-28">
        <div className="mx-auto max-w-[1000px]">
          <h2 className="t-display">Measured, not promised.</h2>
          <div className="mt-12 grid gap-10 sm:grid-cols-3">
            {NUMBERS.map((n) => (
              <div key={n.label}>
                <p className="text-[56px] font-semibold leading-none tracking-tight text-primary-on-dark">
                  <span className="jx-count" data-value={n.v}>0</span>{n.suffix}
                </p>
                <p className="mt-3 t-body text-muted-on-dark">{n.label}</p>
              </div>
            ))}
          </div>
          <p className="mt-10 t-caption text-white/40">Measured on ParhLo&apos;s production system. The summary test used 16 real and deliberately falsified summaries.</p>
        </div>
      </section>

      {/* Decides vs writes */}
      <section className="bg-canvas px-4 py-20 sm:py-28">
        <div className="jx-split mx-auto grid max-w-[1000px] gap-5 md:grid-cols-2">
          <div className="rounded-[18px] bg-parchment p-8">
            <div className="flex items-center gap-3">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/brand/typesafe-jev.png" alt="" width={36} height={36} className="h-9 w-9 rounded-full" />
              <h3 className="t-tagline">Jev decides</h3>
            </div>
            <ul className="mt-4 space-y-2 t-body text-ink-60">
              <li>Typed answers: a choice, a yes or no, or a score</li>
              <li>A probability with every answer</li>
              <li>Fast enough to run on every article, every night</li>
            </ul>
          </div>
          <div className="rounded-[18px] bg-parchment p-8">
            <div className="flex items-center gap-3"><LogoMark size={36} /><h3 className="t-tagline">The language model writes</h3></div>
            <ul className="mt-4 space-y-2 t-body text-ink-60">
              <li>Summaries, written only from the original article</li>
              <li>Headlines, the &ldquo;why this story&rdquo; line and the layout</li>
              <li>Answers when you ask your paper a question</li>
            </ul>
          </div>
          <div className="md:col-span-2 rounded-[18px] border border-hairline p-6 t-body text-ink-60">
            <span className="font-semibold text-ink">If Jev is ever unavailable,</span> a second AI pass checks each summary instead, and the badge on the story says so. A story is only marked ✓ when the check passes. Otherwise it shows &ldquo;AI summary&rdquo; or &ldquo;Based on headline and excerpt&rdquo;, and every story links to the original.
          </div>
        </div>
      </section>

      <section className="bg-parchment px-4 py-20 text-center">
        <h2 className="t-section">See it on your own paper.</h2>
        <p className="t-body mx-auto mt-2 max-w-xl text-ink-60">Hover any &ldquo;Checked against source&rdquo; badge to see Jev&apos;s confidence for that story.</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link href="/paper" className="btn btn-primary">Open my paper</Link>
          <a href="https://typesafe.ai" target="_blank" rel="noopener noreferrer" className="btn btn-secondary">About Jev at typesafe.ai</a>
        </div>
      </section>
    </div>
  );
}
