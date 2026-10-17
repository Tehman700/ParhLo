"use client";

import { AuthenticateWithRedirectCallback } from "@clerk/nextjs";
import { Spinner } from "@/components/ui";
import { CLERK_ENABLED } from "@/lib/auth";

/** Google OAuth lands here; Clerk finishes sign-in (or sign-up) and sends the reader to /start. */
export default function SsoCallback() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-parchment">
      <Spinner label="Signing you in…" />
      {CLERK_ENABLED && <AuthenticateWithRedirectCallback signInFallbackRedirectUrl="/start" signUpFallbackRedirectUrl="/start" />}
    </main>
  );
}
