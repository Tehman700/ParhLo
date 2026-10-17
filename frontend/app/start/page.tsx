"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ErrorNote, Spinner } from "@/components/ui";
import type { Me } from "@/lib/api";
import { PENDING_INVITE, useApi, useSession } from "@/lib/auth";

/** After sign-in: new readers go to onboarding, returning readers to today's paper. */
export default function Start() {
  const router = useRouter();
  const { ready, signedIn } = useSession();
  const api = useApi();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    if (!signedIn) return void router.replace("/");
    (async () => {
      // An invite opened before signing in is accepted now.
      let invite: string | null = null;
      try { invite = localStorage.getItem(PENDING_INVITE); localStorage.removeItem(PENDING_INVITE); } catch {}
      if (invite) await api.post(`/api/invites/${invite}/accept`).catch(() => {});
      const me = await api.get<Me>("/api/me");
      router.replace(!me.user.onboarded ? "/onboarding" : invite ? "/dashboard#friends" : "/paper");
    })().catch((e) => setError(e.message));
  }, [ready, signedIn, api, router]);

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      {error ? <ErrorNote error={error} /> : <Spinner label="Opening your paper…" />}
    </main>
  );
}
