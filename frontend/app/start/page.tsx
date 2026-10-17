"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ErrorNote, Spinner } from "@/components/ui";
import type { Me } from "@/lib/api";
import { useApi, useSession } from "@/lib/auth";

/** After sign-in: new readers go to onboarding, returning readers to today's paper. */
export default function Start() {
  const router = useRouter();
  const { ready, signedIn } = useSession();
  const api = useApi();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    if (!signedIn) return void router.replace("/");
    api.get<Me>("/api/me")
      .then((me) => router.replace(me.user.onboarded ? "/paper" : "/onboarding"))
      .catch((e) => setError(e.message));
  }, [ready, signedIn, api, router]);

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      {error ? <ErrorNote error={error} /> : <Spinner label="Opening your paper…" />}
    </main>
  );
}
