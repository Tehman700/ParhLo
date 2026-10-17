"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { request } from "@/lib/api";
import { useSession } from "@/lib/auth";
import { LogoMark } from "./Logo";
import { Spinner } from "./ui";

gsap.registerPlugin(useGSAP);

type Step = "email" | "code";

const GOOGLE_ERRORS: Record<string, string> = {
  google_cancelled: "Google sign-in was cancelled.",
  google_state: "Your sign-in session expired. Please try again.",
  google_failed: "Google sign-in didn't work. Please try again.",
};

/** Sign in or create an account: Google, or a 6-digit code sent by email. */
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
    gsap.timeline({ defaults: { ease: "power3.out" } })
      .from(".auth-logo", { scale: 0.6, opacity: 0, duration: 0.6 })
      .from(".auth-logo .logo-sun", { y: 14, duration: 0.9 }, "-=0.4")
      .from(".auth-head > *", { y: 16, opacity: 0, stagger: 0.07, duration: 0.55 }, "-=0.6")
      .from(".auth-card", { y: 24, opacity: 0, duration: 0.6 }, "-=0.35")
      .from(".auth-foot", { opacity: 0, duration: 0.5 }, "-=0.2");
  }, { scope: root });

  useGSAP(() => {
    gsap.from(".auth-step > *", { y: 12, opacity: 0, stagger: 0.06, duration: 0.45, ease: "power3.out" });
  }, { scope: root, dependencies: [step] });

  useGSAP(() => {
    if (error) gsap.fromTo(".auth-error", { y: -6, opacity: 0 }, { y: 0, opacity: 1, duration: 0.35 });
  }, { scope: root, dependencies: [error] });

  function google() {
    setBusy("google");
    window.location.href = "/api/auth/google/start";
  }

  async function sendCode(e?: FormEvent) {
    e?.preventDefault();
    setBusy("send");
    setError(null);
    try {
      await request("/api/auth/otp/request", { method: "POST", json: { email: email.trim() } });
      setDigits(["", "", "", "", "", ""]);
      setStep("code");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function verify(code: string) {
    setBusy("verify");
    setError(null);
    try {
      await request("/api/auth/otp/verify", { method: "POST", json: { email: email.trim(), code } });
      await refresh();
      router.push("/start");
    } catch (e) {
      setError((e as Error).message);
      setDigits(["", "", "", "", "", ""]);
      gsap.fromTo(".otp", { x: -10 }, { x: 0, duration: 0.5, ease: "elastic.out(1, 0.3)" });
      (document.getElementById("otp-0") as HTMLInputElement | null)?.focus();
      setBusy(null);
    }
  }

  function setDigit(i: number, v: string) {
    const clean = v.replace(/\D/g, "");
    if (clean.length > 1) { // pasted the whole code
      const next = clean.slice(0, 6).split("");
      setDigits([...next, ...Array(6 - next.length).fill("")]);
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
    <div ref={root} className="flex min-h-screen flex-col bg-parchment">
      <header className="mx-auto flex h-11 w-full max-w-[1024px] items-center px-4">
        <Link href="/" className="flex items-center gap-1.5 text-[14px] font-semibold tracking-tight"><LogoMark size={20} />ParhLo</Link>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-[400px] text-center">
          <LogoMark size={64} className="auth-logo mx-auto" />
          <div className="auth-head mt-6">
            <h1 className="t-section">{step === "email" ? "Sign in to ParhLo" : "Enter the code"}</h1>
            <p className="mt-2 t-body text-ink-60">
              {step === "email" ? "New here? An account is created for you." : <>We sent a 6-digit code to <span className="text-ink">{email}</span>.</>}
            </p>
          </div>

          <div className="auth-card mt-8 rounded-[18px] bg-canvas p-6 text-left sm:p-8">
            <div className="auth-step">
              {step === "email" ? (
                <>
                  <button className="btn btn-light w-full !h-12" onClick={google} disabled={!!busy}>
                    {busy === "google" ? <Spinner label="Opening Google" /> : (
                      <>
                        <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"/><path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"/></svg>
                        Continue with Google
                      </>
                    )}
                  </button>
                  <div className="my-6 flex items-center gap-3 t-caption text-ink-48"><span className="h-px flex-1 bg-hairline" />or<span className="h-px flex-1 bg-hairline" /></div>
                  <form onSubmit={sendCode} className="space-y-3">
                    <label htmlFor="email" className="sr-only">Email</label>
                    <input id="email" className="input" type="email" required autoComplete="email" placeholder="Email"
                      value={email} onChange={(e) => setEmail(e.target.value)} />
                    <button className="btn btn-primary w-full !h-12" disabled={!!busy || !email.includes("@")}>
                      {busy === "send" ? <Spinner dark label="Sending code" /> : "Continue with email"}
                    </button>
                  </form>
                </>
              ) : (
                <>
                  <div className="otp grid grid-cols-6 gap-2">
                    {digits.map((d, i) => (
                      <input key={i} id={`otp-${i}`} value={d} inputMode="numeric" maxLength={6}
                        autoComplete={i === 0 ? "one-time-code" : "off"} aria-label={`Digit ${i + 1}`} autoFocus={i === 0}
                        onChange={(e) => setDigit(i, e.target.value)}
                        onKeyDown={(e) => e.key === "Backspace" && !d && i > 0 && (document.getElementById(`otp-${i - 1}`) as HTMLInputElement | null)?.focus()}
                        className="input !h-14 !px-0 text-center !text-[24px] font-semibold" />
                    ))}
                  </div>
                  <div className="mt-5 flex items-center justify-between t-caption">
                    <button className="link" onClick={() => { setStep("email"); setError(null); }}>Change email</button>
                    <button className="link" onClick={() => sendCode()} disabled={!!busy}>Send a new code</button>
                  </div>
                  {busy === "verify" && <div className="mt-4 text-center"><Spinner label="Signing in" /></div>}
                </>
              )}
            </div>
            {error && <p className="auth-error mt-4 rounded-[12px] bg-[#fff2f2] px-4 py-3 t-caption text-danger" role="alert">{error}</p>}
          </div>

          <p className="auth-foot mt-8 t-caption text-ink-60">
            Want to look around first? <Link href="/demo" className="link">Try the demo</Link>
          </p>
        </div>
      </main>

      <footer className="pb-6 text-center t-fine text-ink-48">By continuing you agree to receive sign-in emails from ParhLo.</footer>
    </div>
  );
}
