"use client";

import { ClerkProvider, useAuth, useClerk } from "@clerk/nextjs";
import { createContext, useCallback, useContext, useMemo, useSyncExternalStore, type ReactNode } from "react";
import { request, type Headers } from "./api";

/** One session API for the app: Clerk (Google / email OTP) when configured, plus demo readers for judges. */
export const CLERK_ENABLED = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
const DEMO_KEY = "parhlo.demoUser";

type Session = {
  ready: boolean;
  signedIn: boolean;
  demoUser: string | null;
  setDemoUser: (id: string | null) => void;
  signOut: () => Promise<void>;
  headers: () => Promise<Headers>;
};

const Ctx = createContext<Session | null>(null);

const listeners = new Set<() => void>();
const readDemo = () => {
  try {
    return localStorage.getItem(DEMO_KEY);
  } catch {
    return null;
  }
};
const subscribe = (cb: () => void) => {
  listeners.add(cb);
  window.addEventListener("storage", cb);
  return () => {
    listeners.delete(cb);
    window.removeEventListener("storage", cb);
  };
};

function useDemo() {
  const demoUser = useSyncExternalStore(subscribe, readDemo, () => null);
  const loaded = useSyncExternalStore(subscribe, () => true, () => false);
  const setDemoUser = useCallback((id: string | null) => {
    try {
      if (id) localStorage.setItem(DEMO_KEY, id);
      else localStorage.removeItem(DEMO_KEY);
    } catch {}
    listeners.forEach((l) => l());
  }, []);
  return useMemo(() => ({ demoUser, setDemoUser, loaded }), [demoUser, setDemoUser, loaded]);
}

function ClerkBridge({ children }: { children: ReactNode }) {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const clerk = useClerk();
  const demo = useDemo();
  const value = useMemo<Session>(() => ({
    ready: isLoaded && demo.loaded,
    signedIn: Boolean(isSignedIn) || Boolean(demo.demoUser),
    demoUser: demo.demoUser,
    setDemoUser: demo.setDemoUser,
    signOut: async () => {
      demo.setDemoUser(null);
      if (isSignedIn) await clerk.signOut();
    },
    headers: async (): Promise<Headers> => {
      if (demo.demoUser) return { "X-Demo-User": demo.demoUser };
      const token = await getToken();
      return token ? { Authorization: `Bearer ${token}` } : {};
    },
  }), [isLoaded, isSignedIn, getToken, clerk, demo]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

function DemoOnly({ children }: { children: ReactNode }) {
  const demo = useDemo();
  const value = useMemo<Session>(() => ({
    ready: demo.loaded,
    signedIn: Boolean(demo.demoUser),
    demoUser: demo.demoUser,
    setDemoUser: demo.setDemoUser,
    signOut: async () => demo.setDemoUser(null),
    headers: async (): Promise<Headers> => (demo.demoUser ? { "X-Demo-User": demo.demoUser } : {}),
  }), [demo]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  if (CLERK_ENABLED) {
    return (
      <ClerkProvider afterSignOutUrl="/" signInFallbackRedirectUrl="/start" signUpFallbackRedirectUrl="/start">
        <ClerkBridge>{children}</ClerkBridge>
      </ClerkProvider>
    );
  }
  return <DemoOnly>{children}</DemoOnly>;
}

export function useSession(): Session {
  const s = useContext(Ctx);
  if (!s) throw new Error("useSession must be used inside AuthProvider");
  return s;
}

/** Authenticated API helpers bound to the current session. */
export function useApi() {
  const { headers } = useSession();
  return useMemo(() => ({
    get: async <T,>(path: string) => request<T>(path, { headers: await headers() }),
    post: async <T,>(path: string, json?: unknown) => request<T>(path, { method: "POST", json: json ?? {}, headers: await headers() }),
    patch: async <T,>(path: string, json: unknown) => request<T>(path, { method: "PATCH", json, headers: await headers() }),
    del: async <T,>(path: string) => request<T>(path, { method: "DELETE", headers: await headers() }),
  }), [headers]);
}
