"use client";

import Link from "next/link";
import { AuthCard } from "@/components/AuthCard";
import { Logo } from "@/components/Logo";
import { CLERK_ENABLED } from "@/lib/auth";

export default function SignInPage() {
  if (CLERK_ENABLED) return <AuthCard />;
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-parchment p-6 text-center">
      <Logo size={40} />
      <p className="text-ink-60">Sign-in is being set up. <Link className="font-semibold text-primary" href="/demo">Try a demo reader</Link> meanwhile.</p>
    </main>
  );
}
