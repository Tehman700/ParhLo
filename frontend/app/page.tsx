"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Link from "next/link";
import { useRef } from "react";
import { LogoMark } from "@/components/Logo";
import { TopBar } from "@/components/ui";
import { CLERK_ENABLED } from "@/lib/auth";

gsap.registerPlugin(ScrollTrigger, useGSAP);

const STATS = [
  { value: 42, suffix: "%", label: "of people now avoid the news — mostly because it's too much.", src: "Reuters Institute, 2026" },
  { value: 51, suffix: "%", label: "of AI news answers had significant errors in a BBC study.", src: "BBC, 2025" },
  { value: 37, suffix: "%", label: "trust in news — the lowest ever recorded.", src: "Reuters Institute, 2026" },
];

const FEATURES = [
  { icon: "◎", title: "Learns what you care about", body: "Every read, skip and 👍 teaches your paper. Tomorrow's edition is sharper than today's — and you can see why." },
  { icon: "✓", title: "Summaries that show their work", body: "Written only from the original article, then fact-checked against it. Every story links to its source." },
  { icon: "▤", title: "A real newspaper", body: "Masthead, lead story, columns. Read it on the web or download today's edition as a print-ready PDF." },
  { icon: "☀", title: "Your morning box", body: "Weather, air quality with smog alerts, the rupee rate and the cricket — the things you check every morning." },
  { icon: "⇆", title: "One story, every outlet", body: "Dawn, Geo, BBC and more covering the same event, grouped into one card. No more tab-hopping." },
  { icon: "③", title: "Three things to remember", body: "A paper that ends. Finish in your reading time and walk away knowing three things — then prove it in tomorrow's quiz." },
];

export default function Landing() {
  const root = useRef<HTMLDivElement>(null);
  const start = CLERK_ENABLED ? "/sign-up" : "/demo";

  useGSAP(() => {
    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
    tl.from(".hero-mark .logo-sun", { y: 18, duration: 1.1, ease: "power2.out" })
      .from(".hero-mark .logo-rays line", { scale: 0, transformOrigin: "32px 37px", opacity: 0, stagger: 0.06, duration: 0.5 }, "-=0.6")
      .from(".hero-mark .logo-line", { scaleX: 0, transformOrigin: "left center", stagger: 0.12, duration: 0.5 }, "-=0.3")
      .from(".hero-word", { yPercent: 110, opacity: 0, stagger: 0.07, duration: 0.8 }, "-=0.5")
      .from(".hero-sub", { y: 16, opacity: 0, duration: 0.6 }, "-=0.4")
      .from(".hero-cta > *", { y: 12, opacity: 0, stagger: 0.08, duration: 0.5 }, "-=0.3")
      .from(".hero-paper", { rotateX: 55, y: 120, opacity: 0, duration: 1.3, ease: "power4.out" }, "-=0.6")
      .from(".hero-paper .col", { opacity: 0, y: 14, stagger: 0.08, duration: 0.5 }, "-=0.7");

    gsap.to(".hero-paper", {
      rotateX: 0, y: -40, ease: "none",
      scrollTrigger: { trigger: ".hero-paper", start: "top 80%", end: "bottom top", scrub: true },
    });

    gsap.utils.toArray<HTMLElement>(".stat-num").forEach((el) => {
      const target = Number(el.dataset.value);
      const obj = { v: 0 };
      gsap.to(obj, {
        v: target, duration: 1.6, ease: "power2.out",
        scrollTrigger: { trigger: el, start: "top 85%" },
        onUpdate: () => (el.textContent = `${Math.round(obj.v)}`),
      });
    });
    gsap.from(".feature", {
      y: 40, opacity: 0, stagger: 0.08, duration: 0.7, ease: "power3.out",
      scrollTrigger: { trigger: ".features", start: "top 75%" },
    });
    gsap.from(".step", {
      x: -30, opacity: 0, stagger: 0.15, duration: 0.6,
      scrollTrigger: { trigger: ".steps", start: "top 75%" },
    });
  }, { scope: root });

  return (
    <div ref={root}>
      <TopBar />

      {/* Hero */}
      <section className="overflow-hidden px-4 pb-10 pt-16 text-center sm:pt-24">
        <LogoMark size={88} className="hero-mark mx-auto" />
        <h1 className="font-masthead mx-auto mt-8 max-w-4xl text-[44px] font-bold leading-[1.04] tracking-tight sm:text-[76px]">
          {["Your", "morning", "paper,"].map((w) => (
            <span key={w} className="inline-block overflow-hidden align-bottom"><span className="hero-word inline-block pr-[0.22em]">{w}</span></span>
          ))}
          <br />
          {["made", "for"].map((w) => (
            <span key={w} className="inline-block overflow-hidden align-bottom"><span className="hero-word inline-block pr-[0.22em]">{w}</span></span>
          ))}
          <span className="inline-block overflow-hidden align-bottom"><span className="hero-word inline-block italic text-sun-deep">you.</span></span>
        </h1>
        <p className="hero-sub mx-auto mt-6 max-w-xl text-[19px] text-ink-60">
          ParhLo reads the whole web every night — Dawn to the BBC — and hands you one finite, verified newspaper that learns what you care about.
        </p>
        <div className="hero-cta mt-8 flex flex-wrap justify-center gap-3">
          <Link href={start} className="btn btn-primary !px-7 !py-3.5 !text-[17px]">Get my paper</Link>
          <Link href="/demo" className="btn btn-secondary !px-7 !py-3.5 !text-[17px]">See a demo reader</Link>
        </div>

        {/* Paper preview */}
        <div className="mx-auto mt-16 max-w-4xl [perspective:1400px]">
          <div className="hero-paper paper rounded-[6px] p-6 text-left shadow-[0_30px_80px_-20px_rgba(0,0,0,0.35)] sm:p-10">
            <div className="flex items-end justify-between border-b border-ink pb-2 text-[11px] text-ink-60">
              <span>No. 12 · Lahore · 28°C · AQI 152 ⚠</span><span>Saturday, 17 October 2026</span>
            </div>
            <div className="py-3 text-center font-masthead text-[44px] font-black leading-none sm:text-[64px]">Parh<span className="italic text-sun-deep">Lo</span></div>
            <div className="double-rule" />
            <div className="mt-5 grid gap-6 sm:grid-cols-3">
              <div className="col sm:col-span-2 sm:border-r sm:border-rule sm:pr-6">
                <p className="kicker text-sun-deep">Lead · Technology</p>
                <h3 className="headline mt-2 text-[28px]">The story that matters most to you, today</h3>
                <p className="deck dropcap mt-3">Your lead story is picked from hundreds of articles across Pakistan and the world, summarised only from the source, and checked before it reaches you.</p>
                <p className="mt-3 caption text-success">✓ Verified against source · Also reported by Dawn, BBC, Geo</p>
              </div>
              <div className="col space-y-4">
                <div className="rounded-[4px] bg-ink p-4 text-white">
                  <p className="kicker text-sun">3 things to remember</p>
                  <ol className="mt-2 list-decimal space-y-1 pl-4 font-serif text-[14px] text-white/85">
                    <li>Short. Memorable. Yours.</li><li>Pulled from today&apos;s paper.</li><li>Quizzed tomorrow.</li>
                  </ol>
                </div>
                <div className="border-t border-rule pt-3">
                  <p className="kicker text-ink-48">Cricket</p>
                  <p className="headline mt-1 text-[18px]">Grouped from every outlet</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Why */}
      <section className="bg-tile px-4 py-20 text-white sm:py-28">
        <div className="mx-auto max-w-[1100px]">
          <h2 className="font-masthead text-[34px] font-bold sm:text-[48px]">News is broken in three ways.</h2>
          <div className="mt-12 grid gap-10 sm:grid-cols-3">
            {STATS.map((s) => (
              <div key={s.label}>
                <div className="font-masthead text-[64px] font-bold leading-none text-sun">
                  <span className="stat-num" data-value={s.value}>0</span>{s.suffix}
                </div>
                <p className="mt-3 text-[17px] text-white/80">{s.label}</p>
                <p className="mt-2 text-[12px] text-white/40">{s.src}</p>
              </div>
            ))}
          </div>
          <p className="mt-14 max-w-2xl text-[21px] text-white/90">
            ParhLo&apos;s answer: a paper that <em className="text-sun not-italic">ends</em>, summaries that <em className="text-sun not-italic">show their sources</em>, and a feed that is <em className="text-sun not-italic">yours</em>.
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="features mx-auto max-w-[1100px] px-4 py-20 sm:py-28">
        <h2 className="display text-center text-[34px] sm:text-[44px]">Everything a morning needs.</h2>
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="feature card">
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-newsprint text-[20px] text-sun-deep">{f.icon}</div>
              <h3 className="mt-4 text-[19px] font-semibold">{f.title}</h3>
              <p className="mt-2 text-[15px] text-ink-60">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="bg-white px-4 py-20 sm:py-28">
        <div className="steps mx-auto max-w-[900px]">
          <h2 className="display text-[34px] sm:text-[44px]">Sixty seconds to your first edition.</h2>
          {[
            ["Tell us what you love", "Pick topics, follow names, swipe on today's real headlines."],
            ["We print your paper", "Hundreds of articles ranked, summarised, verified and laid out for you."],
            ["It learns every morning", "Read, skip, react. Watch your paper adapt — and see exactly why."],
          ].map(([t, b], i) => (
            <div key={t} className="step mt-8 flex gap-5">
              <div className="font-masthead text-[44px] font-bold leading-none text-sun-deep">{i + 1}</div>
              <div>
                <h3 className="text-[21px] font-semibold">{t}</h3>
                <p className="mt-1 text-[17px] text-ink-60">{b}</p>
              </div>
            </div>
          ))}
          <Link href={start} className="btn btn-primary mt-12 !px-7 !py-3.5 !text-[17px]">Start reading — it&apos;s free</Link>
        </div>
      </section>

      <footer className="px-4 py-10 text-center text-[12px] text-ink-48">
        ParhLo · Built for NaSCon&apos;26 · Summaries are AI-generated from linked sources — always one tap from the original.
      </footer>
    </div>
  );
}
