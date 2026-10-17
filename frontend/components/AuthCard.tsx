"use client";

import { useSignIn, useSignUp } from "@clerk/nextjs/legacy";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState, type FormEvent } from "react";
import { Logo, LogoMark } from "./Logo";
import { Spinner } from "./ui";

gsap.registerPlugin(useGSAP);

type Step = "email" | "code";
type Mode = "signIn" | "signUp";

/** Clerk error → readable sentence. */
function message(err: unknown): string {
  const e = err as { errors?: { longMessage?: string; message?: string; code?: string }[]; message?: string };
  return e.errors?.[0]?.longMessage ?? e.errors?.[0]?.message ?? e.message ?? "Something went wrong. Please try again.";
}
const code0 = (err: unknown) => (err as { errors?: { code?: string }[] }).errors?.[0]?.code;

/** ParhLo's own sign-in: Continue with Google, or a 6-digit email code (new readers are signed up automatically). */
export function AuthCard() {
  const router = useRouter();
  const { isLoaded: inLoaded, signIn, setActive } = useSignIn();
  const { isLoaded: upLoaded, signUp } = useSignUp();
  const root = useRef<HTMLDivElement>(null);
  const [step, setStep] = useState<Step>("email");
  const [mode, setMode] = useState<Mode>("signIn");
  const [email, setEmail] = useState("");
  const [digits, setDigits] = useState(["", "", "", "", "", ""]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ready = inLoaded && upLoaded;

  useGSAP(() => {
    gsap.from(".auth-panel > *", { y: 24, opacity: 0, stagger: 0.08, duration: 0.6, ease: "power3.out" });
    gsap.from(".auth-mark .logo-sun", { y: 16, duration: 1.2, ease: "power2.out" });
    gsap.from(".auth-paper", { rotate: -6, y: 60, opacity: 0, duration: 1.1, ease: "power3.out", delay: 0.2 });
  }, { scope: root });

  useGSAP(() => {
    gsap.from(".auth-step > *", { x: 30, opacity: 0, stagger: 0.06, duration: 0.45, ease: "power3.out" });
  }, { scope: root, dependencies: [step] });

  async function google() {
    if (!signIn) return;
    setBusy("Opening Google…");
    setError(null);
    try {
      await signIn.authenticateWithRedirect({ strategy: "oauth_google", redirectUrl: "/sso-callback", redirectUrlComplete: "/start" });
    } catch (e) {
      setError(message(e));
      setBusy(null);
    }
  }

  async function sendCode(e?: FormEvent) {
    e?.preventDefault();
    if (!signIn || !signUp) return;
    setBusy("Sending your code…");
    setError(null);
    try {
      // Existing reader → sign in with an email code.
      const attempt = await signIn.create({ identifier: email.trim() });
      const factor = attempt.supportedFirstFactors?.find((f) => f.strategy === "email_code") as { emailAddressId: string } | undefined;
      if (!factor) throw new Error("Email codes aren't enabled for this account.");
      await signIn.prepareFirstFactor({ strategy: "email_code", emailAddressId: factor.emailAddressId });
      setMode("signIn");
      setStep("code");
    } catch (err) {
      if (code0(err) === "form_identifier_not_found") {
        // New reader → create the account, verify the email with a code.
        try {
          await signUp.create({ emailAddress: email.trim() });
          await signUp.prepareEmailAddressVerification({ strategy: "email_code" });
          setMode("signUp");
          setStep("code");
        } catch (e2) {
          setError(message(e2));
        }
      } else setError(message(err));
    } finally {
      setBusy(null);
    }
  }

  async function verify(code: string) {
    if (!signIn || !signUp || !setActive) return;
    setBusy("Checking the code…");
    setError(null);
    try {
      const res = mode === "signIn"
        ? await signIn.attemptFirstFactor({ strategy: "email_code", code })
        : await signUp.attemptEmailAddressVerification({ code });
      if (res.status === "complete" && res.createdSessionId) {
        await setActive({ session: res.createdSessionId });
        router.push("/start");
        return;
      }
      setError(res.status === "missing_requirements"
        ? `Your Clerk settings require more fields (${(res as { missingFields?: string[] }).missingFields?.join(", ")}). Turn off "password" in Clerk.`
        : "Couldn't finish signing in. Please try again.");
    } catch (e) {
      setError(message(e));
      setDigits(["", "", "", "", "", ""]);
      gsap.fromTo(".otp", { x: -8 }, { x: 0, duration: 0.4, ease: "elastic.out(1, 0.3)" });
    } finally {
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
                <button className="btn btn-light w-full !py-3.5" onClick={google} disabled={!ready || !!busy}>
                  <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"/><path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"/></svg>
                  Continue with Google
                </button>
                <div className="my-6 flex items-center gap-3 text-[13px] text-ink-48"><span className="h-px flex-1 bg-hairline" />or with email<span className="h-px flex-1 bg-hairline" /></div>
                <form onSubmit={sendCode} className="space-y-3">
                  <input className="input" type="email" required autoComplete="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
                  <button className="btn btn-primary w-full !py-3.5" disabled={!ready || !!busy || !email.includes("@")}>
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

          {/* Clerk bot protection renders here; must stay mounted through the whole flow */}
          <div id="clerk-captcha" className="mt-3" />

          {error && <p className="mt-4 rounded-[11px] bg-[#fbe9e7] px-4 py-3 text-[14px] text-danger" role="alert">{error}</p>}

          <p className="mt-10 border-t border-hairline pt-6 text-center text-[14px] text-ink-60">
            Just looking? <Link href="/demo" className="font-semibold text-primary">Try a demo reader</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
