"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { AuthCard } from "@/components/AuthCard";
import { useSession } from "@/lib/auth";

export default function SignInPage() {
  const router = useRouter();
  const { user } = useSession();
  // Already signed in: skip the form.
  useEffect(() => {
    if (user) router.replace("/start");
  }, [user, router]);
  return <AuthCard />;
}
