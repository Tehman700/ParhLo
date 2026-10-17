"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Link from "next/link";
import { useRef } from "react";
import { MotionLoop } from "@/components/MotionLoop";
import { BrowserFrame, PaperMock } from "@/components/PaperMock";
import { StartButtons, TopBar } from "@/components/ui";

gsap.registerPlugin(ScrollTrigger, useGSAP);

const INTERESTS = [
  { label: "Technology", value: 92 }, { label: "Cricket", value: 78 }, { label: "Economy", value: 64 },
  { label: "Formula 1", value: 51 }, { label: "Health", value: 22 },
];

export default function Landing() {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    gsap.timeline({ defaults: { ease: "power3.out" } })
      .from(".hero-eyebrow", { y: 10, opacity: 0, duration: 0.5 })
      .from(".hero-title", { y: 24, opacity: 0, duration: 0.8 }, "-=0.25")
      .from(".hero-sub", { y: 16, opacity: 0, duration: 0.6 }, "-=0.5")
      .from(".hero-cta > *", { y: 10, opacity: 0, stagger: 0.08, duration: 0.5 }, "-=0.35")
      .from(".hero-product", { y: 80, opacity: 0, scale: 0.94, duration: 1.2, ease: "power4.out" }, "-=0.35");

    // The product settles as you scroll past it.
    gsap.to(".hero-product", { y: -40, ease: "none", scrollTrigger: { trigger: ".hero-product", start: "top 70%", end: "bottom top", scrub: true } });

    // Every tile: headline and copy rise in, the visual follows.
    gsap.utils.toArray<HTMLElement>(".tile").forEach((tile) => {
      gsap.from(tile.querySelectorAll(".reveal"), {
        y: 40, opacity: 0, stagger: 0.1, duration: 0.8, ease: "power3.out",
        scrollTrigger: { trigger: tile, start: "top 75%" },
      });
    });

    // Left/right pairs: copy enters from the left, the visual from the right; reverses when scrolled back up.
    gsap.utils.toArray<HTMLElement>(".slide-pair").forEach((pair) => {
      const st = { trigger: pair, start: "top 75%", toggleActions: "play none none reverse" };
      gsap.from(pair.querySelectorAll(".slide-left"), { x: -80, opacity: 0, duration: 0.9, ease: "power3.out", scrollTrigger: st });
      gsap.from(pair.querySelectorAll(".slide-right"), { x: 80, opacity: 0, duration: 0.9, ease: "power3.out", delay: 0.08, scrollTrigger: st });
    });

    gsap.from(".interest-bar", {
      width: 0, duration: 1.2, stagger: 0.1, ease: "power3.out",
      scrollTrigger: { trigger: ".interest-bars", start: "top 80%" },
    });
    gsap.utils.toArray<HTMLElement>(".count").forEach((el) => {
      const obj = { v: 0 };
      gsap.to(obj, {
        v: Number(el.dataset.value), duration: 1.4, ease: "power2.out",
        scrollTrigger: { trigger: el, start: "top 85%" },
        onUpdate: () => (el.textContent = String(Math.round(obj.v))),
      });
    });
    gsap.from(".pdf-page", {
      rotate: -8, y: 60, opacity: 0, duration: 1, ease: "power3.out", stagger: 0.12,
      scrollTrigger: { trigger: ".pdf-stack", start: "top 80%" },
    });
  }, { scope: root });

  return (
    <div ref={root} className="overflow-x-hidden">
      <TopBar />

      {/* Hero */}
      <section className="bg-parchment px-4 pt-16 text-center sm:pt-24">
        <p className="hero-eyebrow t-tagline text-ink-60">ParhLo</p>
        <h1 className="hero-title t-hero mx-auto mt-3 max-w-3xl">Your news, in one paper.</h1>
        <p className="hero-sub t-lead mx-auto mt-4 max-w-2xl text-ink-60">
          ParhLo reads the news for you each night and puts what you care about into one short paper every morning.
        </p>
        <div className="hero-cta mt-8"><StartButtons /></div>
        <div className="mx-auto mt-14 max-w-[880px]">
          <BrowserFrame className="hero-product rounded-b-none">
            <PaperMock />
          </BrowserFrame>
        </div>
      </section>

      {/* One shape: the whole product in 14 seconds. Copy slides in from the left, the loop from the right. */}
      <section className="slide-pair overflow-hidden bg-canvas px-4 py-24 sm:py-32">
        <div className="mx-auto grid max-w-[980px] items-center gap-12 md:grid-cols-[1fr_1.1fr]">
          <div className="slide-left">
            <p className="t-tagline text-ink-60">Your morning, in one place</p>
            <h2 className="t-display mt-2">Everything your paper does, in one place.</h2>
            <ul className="mt-6 space-y-3 t-body text-ink-60">
              <li><span className="font-semibold text-ink">Printed by morning.</span> Your paper is ready when you wake up.</li>
              <li><span className="font-semibold text-ink">Your reading time.</span> Pick 5, 10, 15 or 20 minutes.</li>
              <li><span className="font-semibold text-ink">Your topics.</span> Switch them on and off, and see what it has learned.</li>
              <li><span className="font-semibold text-ink">Ask your paper.</span> Questions answered from your stories, with sources.</li>
            </ul>
          </div>
          <div className="slide-right">
            <MotionLoop bg="ffffff" />
          </div>
        </div>
      </section>

      {/* It learns */}
      <section className="tile tile-dark px-4 py-24 sm:py-32">
        <div className="mx-auto grid max-w-[980px] items-center gap-14 md:grid-cols-2">
          <div>
            <h2 className="reveal t-display">It learns what you like.</h2>
            <p className="reveal t-lead mt-4 text-muted-on-dark">Read, skip or like a story. Tomorrow&apos;s paper changes to match, and you can see why.</p>
            <Link href="/how-it-works" className="reveal link-on-dark mt-6 inline-block t-body">See how it works ›</Link>
          </div>
          <div className="reveal interest-bars rounded-[18px] bg-tile-2 p-7">
            <p className="t-caption text-muted-on-dark">Your interests</p>
            <div className="mt-5 space-y-4">
              {INTERESTS.map((i) => (
                <div key={i.label} className="grid grid-cols-[110px_1fr_32px] items-center gap-3 t-caption">
                  <span>{i.label}</span>
                  <div className="h-2 overflow-hidden rounded-full bg-white/10">
                    <div className="interest-bar h-full rounded-full bg-primary-on-dark" style={{ width: `${i.value}%` }} />
                  </div>
                  <span className="text-right text-muted-on-dark">{i.value}</span>
                </div>
              ))}
            </div>
            <p className="mt-6 t-caption text-muted-on-dark">▲ Formula 1 went up because you read 4 race stories this week.</p>
          </div>
        </div>
      </section>

      {/* Checked summaries */}
      <section className="tile bg-canvas px-4 py-24 text-center sm:py-32">
        <h2 className="reveal t-display mx-auto max-w-2xl">Every summary is checked.</h2>
        <p className="reveal t-lead mx-auto mt-4 max-w-2xl text-ink-60">Summaries are written from the original article, then checked against it. Every story links to its source.</p>
        <div className="reveal mx-auto mt-12 max-w-[560px] rounded-[18px] border border-hairline p-6 text-left">
          <p className="kicker">Pakistan</p>
          <p className="headline mt-2 text-[22px]">Government announces relief package for flood-hit districts</p>
          <p className="deck mt-2 text-[15px]">The package covers rebuilding homes and schools in eleven districts and will be paid in two parts this year.</p>
          <div className="mt-4 flex flex-wrap items-center gap-2 t-caption">
            <span className="rounded-full bg-[#e9f6ec] px-3 py-1 font-semibold text-success">✓ Checked against source</span>
            <span className="rounded-full bg-parchment px-3 py-1 text-ink-60">Dawn</span>
            <span className="rounded-full bg-parchment px-3 py-1 text-ink-60">Geo News</span>
            <span className="rounded-full bg-parchment px-3 py-1 text-ink-60">BBC</span>
          </div>
        </div>
        <div className="reveal mx-auto mt-14 grid max-w-[820px] gap-8 sm:grid-cols-3">
          {[{ v: 51, t: "of AI news answers had major errors in a BBC study." }, { v: 42, t: "of people now avoid the news." }, { v: 37, t: "of people trust the news they see." }].map((s) => (
            <div key={s.t}>
              <p className="t-display text-primary"><span className="count" data-value={s.v}>0</span>%</p>
              <p className="mt-2 t-caption text-ink-60">{s.t}</p>
            </div>
          ))}
        </div>
        <p className="reveal mt-6 t-fine text-ink-48">Sources: BBC (2025), Reuters Institute Digital News Report (2026).</p>
      </section>

      {/* PDF */}
      <section className="tile bg-parchment px-4 py-24 sm:py-32">
        <div className="mx-auto grid max-w-[980px] items-center gap-14 md:grid-cols-2">
          <div className="pdf-stack relative mx-auto h-[360px] w-[280px]">
            <div className="pdf-page absolute left-6 top-6 h-[340px] w-[250px] rotate-[4deg] rounded-[4px] bg-canvas product-shadow" />
            <div className="pdf-page absolute left-0 top-0 h-[340px] w-[250px] rounded-[4px] bg-canvas p-5 product-shadow">
              <div className="masthead text-center text-[30px]">ParhLo</div>
              <div className="double-rule mt-2" />
              <div className="mt-3 h-20 rounded-[3px] bg-[#e8eef6]" />
              <div className="mt-3 space-y-1.5">{[90, 100, 84, 96, 70].map((w, i) => <div key={i} className="h-1.5 rounded-full bg-ink/15" style={{ width: `${w}%` }} />)}</div>
              <div className="mt-4 grid grid-cols-3 gap-2">{[0, 1, 2].map((c) => <div key={c} className="space-y-1.5">{[100, 80, 92, 70].map((w, i) => <div key={i} className="h-1 rounded-full bg-ink/10" style={{ width: `${w}%` }} />)}</div>)}</div>
            </div>
          </div>
          <div>
            <h2 className="reveal t-display">Read it here, or as a PDF.</h2>
            <p className="reveal t-lead mt-4 text-ink-60">Every paper is laid out like a real newspaper. Download it, print it, or read it offline. Past papers are always there.</p>
            <Link href="/demo" className="reveal link mt-6 inline-block t-body">Open a sample paper ›</Link>
          </div>
        </div>
      </section>

      {/* Morning box */}
      <section className="tile tile-dark px-4 py-24 text-center sm:py-32">
        <h2 className="reveal t-display mx-auto max-w-2xl">What you check every morning.</h2>
        <p className="reveal t-lead mx-auto mt-4 max-w-2xl text-muted-on-dark">Weather, air quality, the rupee and the cricket, at the top of every paper.</p>
        <div className="reveal mx-auto mt-12 grid max-w-[880px] gap-3 text-left sm:grid-cols-4">
          {[
            { k: "Lahore", v: "28°", s: "Clear sky" },
            { k: "Air quality", v: "152", s: "Unhealthy. Wear a mask.", alert: true },
            { k: "US dollar", v: "Rs 277", s: "Today's rate" },
            { k: "Cricket", v: "PAK won", s: "By 6 wickets" },
          ].map((c) => (
            <div key={c.k} className="rounded-[18px] bg-tile-2 p-5">
              <p className={`t-caption ${c.alert ? "text-[#ff6961]" : "text-muted-on-dark"}`}>{c.k}</p>
              <p className="mt-2 text-[28px] font-semibold tracking-tight">{c.v}</p>
              <p className="t-caption text-muted-on-dark">{c.s}</p>
            </div>
          ))}
        </div>
      </section>

      {/* More */}
      <section className="tile bg-canvas px-4 py-24 sm:py-32">
        <h2 className="reveal t-display text-center">A few more things.</h2>
        <div className="mx-auto mt-12 grid max-w-[980px] gap-5 sm:grid-cols-3">
          {[
            { t: "One story, every outlet", b: "When Dawn, Geo and the BBC cover the same event, you see it once, with all the sources." },
            { t: "Three things to remember", b: "Each paper ends with three key points, and a short quiz the next morning." },
            { t: "A paper that ends", b: "No endless feed. Your paper fits the time you choose: 5, 10 or 20 minutes." },
          ].map((f) => (
            <div key={f.t} className="reveal rounded-[18px] bg-parchment p-7">
              <h3 className="t-tagline">{f.t}</h3>
              <p className="mt-2 t-body text-ink-60">{f.b}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="tile bg-parchment px-4 py-24 text-center sm:py-28">
        <h2 className="reveal t-display">Start your first paper.</h2>
        <p className="reveal t-lead mx-auto mt-3 max-w-xl text-ink-60">It takes about a minute.</p>
        <div className="reveal mt-8"><StartButtons /></div>
      </section>

    </div>
  );
}
