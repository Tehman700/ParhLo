"use client";

import { SignUp } from "@clerk/nextjs";
import Link from "next/link";
import { Logo } from "@/components/Logo";
import { CLERK_ENABLED } from "@/lib/auth";

export default function SignUpPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 bg-newsprint p-6">
      <Link href="/"><Logo size={40} /></Link>
      {CLERK_ENABLED ? <SignUp /> : <p className="text-ink-60">Sign-up isn&apos;t configured yet. <Link className="text-primary" href="/demo">Try a demo reader</Link>.</p>}
    </main>
  );
}
