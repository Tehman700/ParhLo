"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { request } from "@/lib/api";
import { useSession } from "@/lib/auth";
import { CONTACT_EMAIL } from "@/lib/site";
import { Spinner, TopBar } from "./ui";

gsap.registerPlugin(useGSAP);

const TOPICS: { id: string; label: string; hint: string }[] = [
  { id: "question", label: "A question", hint: "Ask us anything about ParhLo." },
  { id: "problem", label: "Something isn't working", hint: "What did you do, and what happened? Your browser or phone helps too." },
  { id: "summary", label: "A summary looks wrong", hint: "Tell us which story and what's wrong. We check every report against the original article." },
  { id: "idea", label: "An idea for ParhLo", hint: "What would make your morning paper better?" },
  { id: "sources", label: "Suggest a news source", hint: "Which outlet or feed should ParhLo read?" },
  { id: "account", label: "My account or privacy", hint: "Questions about your data, your email or deleting your account." },
  { id: "press", label: "Press or partnership", hint: "Tell us who you are and what you have in mind." },
];

const FAQ: { q: string; a: ReactNode }[] = [
  { q: "Why is a story in my paper?", a: <>Every story says why it&apos;s there, under the summary: something you follow, a topic you like, one of the day&apos;s two biggest stories, something new for you, or a friend&apos;s pick.</> },
  { q: "How do I change what I get?", a: <>Open your <Link href="/dashboard" className="link">dashboard</Link>: switch topics on or off, follow people, teams or companies, or describe your interests. Today&apos;s paper updates in a few seconds. You can also search the news and tap <strong>Follow</strong>.</> },
  { q: "A summary looks wrong. What should I do?", a: <>Summaries are written by AI from the original article and checked against it (that&apos;s the ✓), but mistakes can happen. Every story links to the original. Send us a message below with the topic <strong>A summary looks wrong</strong> and we&apos;ll look at it.</> },
  { q: "When does my paper arrive?", a: <>A new paper is printed every morning around 5:30 AM (Pakistan time), and the morning email arrives at about 6:00 AM. You can turn the email off on your dashboard or with the link in any email.</> },
  { q: "Can I read it offline or print it?", a: <>Yes. Every paper has a <strong>Download PDF</strong> button, laid out like a newspaper. Past papers stay in <Link href="/archive" className="link">Past papers</Link>.</> },
  { q: "How do friends work?", a: <>Invite friends from your dashboard. If you both turn on <strong>Learn from friends</strong>, up to two stories they liked can appear in your paper, labelled with their name. It&apos;s off by default.</> },
  { q: "What does ParhLo know about me?", a: <>Everything it uses is on your dashboard under <strong>What ParhLo remembers</strong>, and you can remove any of it. The <Link href="/privacy" className="link">Privacy Policy</Link> explains the rest.</> },
  { q: "How do I delete my account?", a: <>Dashboard → Account → <strong>Delete account</strong>. Your profile, interests, reading history and papers are deleted straight away.</> },
  { q: "Where does the news come from?", a: <>Trusted outlets in Pakistan and around the world, including Dawn, Express Tribune, Geo News, BBC, The Guardian and specialist sources. See <Link href="/how-it-works" className="link">How it works</Link>, or suggest a source below.</> },
];

function Faq() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <div className="divide-y divide-divider rounded-[18px] bg-canvas">
      {FAQ.map((f, i) => (
        <div key={f.q} className="faq px-5 sm:px-6">
          <button className="flex w-full items-center justify-between gap-4 py-4 text-left" aria-expanded={open === i}
            onClick={() => setOpen(open === i ? null : i)}>
            <span className="t-body font-semibold">{f.q}</span>
            <span className={`flex h-6 w-6 flex-none items-center justify-center rounded-full bg-parchment text-ink-60 transition-transform ${open === i ? "rotate-45" : ""}`}>+</span>
          </button>
          {open === i && <p className="-mt-1 pb-4 t-body text-ink-80">{f.a}</p>}
        </div>
      ))}
    </div>
  );
}

function ContactForm() {
  const { user } = useSession();
  const [form, setForm] = useState({ name: "", email: "", topic: "question", message: "", page: "", website: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ id: number; email: string } | null>(null);
  const [copied, setCopied] = useState(false);

  // prefill: signed-in reader, and ?topic=summary&story=<link> from a story
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const topic = p.get("topic");
    const story = p.get("story");
    queueMicrotask(() => setForm((f) => ({
      ...f,
      topic: topic && TOPICS.some((t) => t.id === topic) ? topic : f.topic,
      page: story ?? f.page,
      name: f.name || (user?.name && user.name !== "Reader" ? user.name : ""),
      email: f.email || user?.email || "",
    })));
  }, [user]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await request<{ id: number; reply_to: string }>("/api/support", { method: "POST", json: { ...form, page: form.page || null } });
      setDone({ id: r.id, email: r.reply_to });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const topic = TOPICS.find((t) => t.id === form.topic)!;
  return (
    <div className="space-y-4">
      <div className="rounded-[18px] bg-canvas p-5 sm:p-6">
        <p className="t-fine font-semibold text-ink-48">Email us directly</p>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <a href={`mailto:${CONTACT_EMAIL}`} className="t-tagline !text-[19px] text-primary hover:underline">{CONTACT_EMAIL}</a>
          <button className="rounded-full bg-parchment px-3 py-1 t-fine text-ink-60 hover:text-ink"
            onClick={() => { navigator.clipboard?.writeText(CONTACT_EMAIL).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1800); }).catch(() => {}); }}>
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
        <p className="mt-1 t-caption text-ink-60">We usually reply within a day.</p>
      </div>

      <div className="rounded-[18px] bg-canvas p-5 sm:p-6">
        {done ? (
          <div className="py-6 text-center" role="status">
            <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#eaf6ec] text-[22px] text-success">✓</span>
            <p className="mt-4 t-tagline">Thanks{form.name ? `, ${form.name}` : ""}. We&apos;ve got your message.</p>
            <p className="mt-2 t-body text-ink-60">We&apos;ll reply to <strong className="text-ink">{done.email}</strong>. Your reference is #{done.id}.</p>
            <button className="btn btn-secondary mt-6" onClick={() => { setDone(null); setForm((f) => ({ ...f, message: "", page: "" })); }}>Send another message</button>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <div>
              <p className="t-tagline">Send us a message</p>
              <p className="mt-1 t-caption text-ink-60">Pick what it&apos;s about so it reaches the right place.</p>
            </div>
            <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="What is it about?">
              {TOPICS.map((t) => (
                <button key={t.id} type="button" role="radio" aria-checked={form.topic === t.id} onClick={() => setForm({ ...form, topic: t.id })}
                  className={`rounded-full px-3.5 py-1.5 t-caption ${form.topic === t.id ? "bg-ink text-white" : "bg-parchment text-ink-80 hover:bg-black/10"}`}>
                  {t.label}
                </button>
              ))}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block"><span className="t-fine font-semibold text-ink-60">Your name</span>
                <input className="input mt-1" required maxLength={80} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
              <label className="block"><span className="t-fine font-semibold text-ink-60">Your email</span>
                <input className="input mt-1" type="email" required maxLength={254} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
            </div>
            {(form.topic === "summary" || form.topic === "problem" || form.page) && (
              <label className="block"><span className="t-fine font-semibold text-ink-60">{form.topic === "summary" ? "Story headline or link" : "Page or link (optional)"}</span>
                <input className="input mt-1" maxLength={300} value={form.page} onChange={(e) => setForm({ ...form, page: e.target.value })} /></label>
            )}
            <label className="block"><span className="t-fine font-semibold text-ink-60">Message</span>
              <textarea className="input mt-1 !h-36 resize-none !py-3 !text-[15px]" required minLength={10} maxLength={4000} placeholder={topic.hint}
                value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} /></label>
            {/* honeypot for bots: hidden from people and screen readers */}
            <input tabIndex={-1} autoComplete="off" aria-hidden className="hidden" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} />
            {error && <p className="rounded-[12px] bg-[#fff2f2] px-4 py-3 t-caption text-danger" role="alert">{error}</p>}
            <div className="flex items-center justify-between gap-3">
              <span className="t-fine text-ink-48">{form.message.length}/4000</span>
              <button className="btn btn-primary" disabled={busy || form.message.trim().length < 10}>{busy ? <Spinner dark label="Sending" /> : "Send message"}</button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

/** /help — common questions, email, and a contact form (messages are emailed to the team and stored). */
export function HelpCenter() {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(() => {
    gsap.from(".help-head > *", { y: 20, opacity: 0, stagger: 0.08, duration: 0.6, ease: "power3.out" });
    gsap.from(".help-col", { y: 24, opacity: 0, stagger: 0.1, duration: 0.6, delay: 0.1, ease: "power3.out" });
  }, { scope: root });
  return (
    <div ref={root} className="min-h-screen bg-parchment">
      <TopBar />
      <header className="pb-10 pt-16">
        <div className="help-head mx-auto max-w-[1024px] px-4">
          <h1 className="t-display">Help &amp; contact</h1>
          <p className="t-lead mt-3 max-w-2xl text-ink-60">Answers to common questions, or send us a message. We read every one.</p>
        </div>
      </header>
      <main className="mx-auto grid max-w-[1024px] gap-6 px-4 pb-20 lg:grid-cols-[1.1fr_1fr]">
        <section className="help-col">
          <h2 className="mb-3 t-tagline">Common questions</h2>
          <Faq />
        </section>
        <section className="help-col lg:sticky lg:top-16 lg:self-start" id="contact">
          <h2 className="mb-3 t-tagline">Contact us</h2>
          <ContactForm />
        </section>
      </main>
    </div>
  );
}
