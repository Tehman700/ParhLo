"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Logo, LogoMark } from "./Logo";
import { Spinner } from "./ui";
import { request } from "@/lib/api";
import { useSession } from "@/lib/auth";

gsap.registerPlugin(useGSAP);

type Step = "email" | "code";

const GOOGLE_ERRORS: Record<string, string> = {
  google_cancelled: "Google sign-in was cancelled.",
  google_state: "Your Google sign-in expired. Please try again.",
  google_failed: "Google sign-in failed. Please try again.",
};

/** ParhLo's own sign-in: Continue with Google, or a 6-digit email code (new readers are created automatically). */
export function AuthCard() {
  const router = useRouter();
  const { refresh } = useSession();
  const root = useRef<HTMLDivElement>(null);
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [digits, setDigits] = useState(["", "", "", "", "", ""]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = new URLSearchParams(window.location.search).get("error");
    if (code && GOOGLE_ERRORS[code]) queueMicrotask(() => setError(GOOGLE_ERRORS[code]));
  }, []);

  useGSAP(() => {
    gsap.from(".auth-panel > *", { y: 24, opacity: 0, stagger: 0.08, duration: 0.6, ease: "power3.out" });
    gsap.from(".auth-mark .logo-sun", { y: 16, duration: 1.2, ease: "power2.out" });
    gsap.from(".auth-paper", { rotate: -6, y: 60, opacity: 0, duration: 1.1, ease: "power3.out", delay: 0.2 });
  }, { scope: root });

  useGSAP(() => {
    gsap.from(".auth-step > *", { x: 30, opacity: 0, stagger: 0.06, duration: 0.45, ease: "power3.out" });
  }, { scope: root, dependencies: [step] });

  function google() {
    setBusy("Opening Google…");
    window.location.href = "/api/auth/google/start";
  }

  async function sendCode(e?: FormEvent) {
    e?.preventDefault();
    setBusy("Sending your code…");
    setError(null);
    try {
      await request("/api/auth/otp/request", { method: "POST", json: { email: email.trim() } });
      setStep("code");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function verify(code: string) {
    setBusy("Checking the code…");
    setError(null);
    try {
      await request("/api/auth/otp/verify", { method: "POST", json: { email: email.trim(), code } });
      await refresh();
      router.push("/start");
    } catch (e) {
      setError((e as Error).message);
      setDigits(["", "", "", "", "", ""]);
      gsap.fromTo(".otp", { x: -8 }, { x: 0, duration: 0.4, ease: "elastic.out(1, 0.3)" });
      setBusy(null);
    }
  }

  function setDigit(i: number, v: string) {
    const clean = v.replace(/\D/g, "");
    if (clean.length > 1) { // pasted the whole code
      const next = clean.slice(0, 6).split("");
      const filled = [...next, ...Array(6 - next.length).fill("")];
      setDigits(filled);
      if (next.length === 6) void verify(next.join(""));
      return;
    }
    const next = [...digits];
    next[i] = clean;
    setDigits(next);
    if (clean && i < 5) (document.getElementById(`otp-${i + 1}`) as HTMLInputElement | null)?.focus();
    if (next.every(Boolean)) void verify(next.join(""));
  }

  return (
    <div ref={root} className="grid min-h-screen lg:grid-cols-2">
      {/* Left: the paper */}
      <div className="relative hidden overflow-hidden bg-tile p-12 text-white lg:flex lg:flex-col">
        <Link href="/" className="text-white"><span className="inline-flex items-center gap-2.5"><LogoMark size={34} /><span className="font-masthead text-[26px]">Parh<span className="italic text-sun">Lo</span></span></span></Link>
        <div className="mt-auto">
          <div className="auth-paper paper max-w-md rotate-[-2deg] rounded-[4px] p-6 text-ink shadow-[0_40px_80px_-30px_rgba(0,0,0,.6)]">
            <div className="flex justify-between border-b border-ink pb-1 text-[10px] text-ink-60"><span>No. 1</span><span>Tomorrow, 6:00 AM</span></div>
            <div className="py-2 text-center font-masthead text-[40px] font-black leading-none">Parh<span className="italic text-sun-deep">Lo</span></div>
            <div className="double-rule" />
            <p className="headline mt-3 text-[20px]">Your first edition is one minute away.</p>
            <p className="deck mt-2 text-[14px]">Tell us what you care about. We&apos;ll read Dawn, Geo, the BBC and twenty more every night — and print only what matters to you.</p>
          </div>
          <p className="mt-10 max-w-md font-serif text-[19px] italic text-white/80">&ldquo;Parh lo&rdquo; — read it. One paper, every morning, that ends.</p>
        </div>
      </div>

      {/* Right: the form */}
      <div className="flex flex-col items-center justify-center bg-parchment px-6 py-12">
        <div className="auth-panel w-full max-w-[400px]">
          <div className="lg:hidden"><Link href="/"><Logo size={34} /></Link></div>
          <LogoMark size={56} className="auth-mark mt-8 hidden lg:block" />
          <h1 className="mt-6 font-masthead text-[36px] font-bold leading-tight">
            {step === "email" ? "Good morning." : "Check your inbox."}
          </h1>
          <p className="mt-2 text-ink-60">
            {step === "email" ? "Sign in or create your paper — no password needed." : <>We sent a 6-digit code to <b className="text-ink">{email}</b>.</>}
          </p>

          <div className="auth-step mt-8">
            {step === "email" ? (
              <>
                <button className="btn btn-light w-full !py-3.5" onClick={google} disabled={!!busy}>
                  <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"/><path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"/></svg>
                  Continue with Google
                </button>
                <div className="my-6 flex items-center gap-3 text-[13px] text-ink-48"><span className="h-px flex-1 bg-hairline" />or with email<span className="h-px flex-1 bg-hairline" /></div>
                <form onSubmit={sendCode} className="space-y-3">
                  <input className="input" type="email" required autoComplete="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
                  <button className="btn btn-primary w-full !py-3.5" disabled={!!busy || !email.includes("@")}>
                    {busy ? <Spinner dark label={busy} /> : "Email me a code"}
                  </button>
                </form>
              </>
            ) : (
              <>
                <div className="otp flex justify-between gap-2">
                  {digits.map((d, i) => (
                    <input key={i} id={`otp-${i}`} value={d} inputMode="numeric" autoComplete={i === 0 ? "one-time-code" : "off"} maxLength={6}
                      aria-label={`Digit ${i + 1}`} autoFocus={i === 0} onChange={(e) => setDigit(i, e.target.value)}
                      onKeyDown={(e) => e.key === "Backspace" && !d && i > 0 && (document.getElementById(`otp-${i - 1}`) as HTMLInputElement | null)?.focus()}
                      className="h-14 w-full rounded-[14px] border border-hairline bg-canvas text-center font-masthead text-[26px] font-bold focus:border-primary focus:outline-none" />
                  ))}
                </div>
                <div className="mt-4 flex items-center justify-between text-[14px]">
                  <button className="text-ink-60 hover:text-ink" onClick={() => { setStep("email"); setDigits(["", "", "", "", "", ""]); setError(null); }}>← Use a different email</button>
                  <button className="font-semibold text-primary" onClick={() => sendCode()} disabled={!!busy}>Resend code</button>
                </div>
                {busy && <div className="mt-4"><Spinner label={busy} /></div>}
              </>
            )}
          </div>

          {error && <p className="mt-4 rounded-[11px] bg-[#fbe9e7] px-4 py-3 text-[14px] text-danger" role="alert">{error}</p>}

          <p className="mt-10 border-t border-hairline pt-6 text-center text-[14px] text-ink-60">
            Just looking? <Link href="/demo" className="font-semibold text-primary">Try a demo reader</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
