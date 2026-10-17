"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { LogoMark } from "@/components/Logo";
import { ErrorNote, Spinner, TopBar } from "@/components/ui";
import { request } from "@/lib/api";
import { PENDING_INVITE, useApi, useSession } from "@/lib/auth";

gsap.registerPlugin(useGSAP);

/** Someone's invite link. Signed-in readers accept here; others sign in first and it's accepted after. */
export default function InvitePage() {
  const { code } = useParams<{ code: string }>();
  const router = useRouter();
  const api = useApi();
  const { ready, user } = useSession();
  const [inviter, setInviter] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [accepted, setAccepted] = useState<string | null>(null);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    request<{ inviter: string }>(`/api/invites/${code}`).then((r) => setInviter(r.inviter)).catch((e) => setError(e.message));
  }, [code]);

  useGSAP(() => {
    if (!inviter) return;
    gsap.timeline({ defaults: { ease: "power3.out" } })
      .from(".inv-logo", { scale: 0.6, opacity: 0, duration: 0.6 })
      .from(".inv-card > *", { y: 16, opacity: 0, stagger: 0.08, duration: 0.55 }, "-=0.3");
  }, { scope: root, dependencies: [inviter] });

  async function accept() {
    if (!user) {
      try { localStorage.setItem(PENDING_INVITE, code); } catch {}
      router.push("/sign-in");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const r = await api.post<{ friend: string }>(`/api/invites/${code}/accept`);
      setAccepted(r.friend);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div ref={root} className="min-h-screen bg-parchment">
      <TopBar />
      <main className="mx-auto flex max-w-[560px] flex-col items-center px-4 py-20 text-center">
        {!inviter && !error && <Spinner label="Opening invite" />}
        {error && !inviter && <ErrorNote error={error} />}
        {inviter && (
          <>
            <div className="inv-logo"><LogoMark size={64} /></div>
            <div className="inv-card mt-8 w-full">
              {accepted ? (
                <>
                  <h1 className="t-display">You and {accepted} are friends.</h1>
                  <p className="t-lead mt-4 text-ink-60">Turn on Learn from friends in your dashboard to see stories {accepted} likes.</p>
                  <div className="mt-8 flex justify-center gap-4">
                    <Link href="/dashboard#friends" className="btn btn-primary">Go to dashboard</Link>
                    <Link href="/paper" className="btn btn-secondary">Today&apos;s paper</Link>
                  </div>
                </>
              ) : (
                <>
                  <h1 className="t-display">{inviter} invited you to ParhLo.</h1>
                  <p className="t-lead mt-4 text-ink-60">One short paper every morning, made around what you read. Accept to become friends.</p>
                  <div className="mt-6"><ErrorNote error={error} /></div>
                  <div className={`mt-8 flex flex-wrap justify-center gap-4 ${ready ? "visible" : "invisible"}`}>
                    <button className="btn btn-primary" onClick={accept} disabled={busy}>
                      {busy ? <Spinner dark label="Accepting" /> : user ? "Accept invite" : "Accept and sign in"}
                    </button>
                    <Link href="/how-it-works" className="btn btn-secondary">What is ParhLo?</Link>
                  </div>
                  {user && <p className="mt-4 t-caption text-ink-48">Signed in as {user.email}</p>}
                </>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
