"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from "react";
import { request, type Headers } from "./api";

/** One session API for the app: our own login (email OTP / Google → httpOnly session cookie) + demo readers. */
const DEMO_KEY = "parhlo.demoUser";

export type SessionUser = { id: string; name: string; email: string | null; onboarded: boolean; is_demo: boolean };

type Session = {
  ready: boolean;
  signedIn: boolean;
  user: SessionUser | null;
  demoUser: string | null;
  setDemoUser: (id: string | null) => void;
  refresh: () => Promise<SessionUser | null>;
  signOut: () => Promise<void>;
  headers: () => Promise<Headers>;
};

const Ctx = createContext<Session | null>(null);

// Demo reader id lives in localStorage (per browser).
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

export function AuthProvider({ children }: { children: ReactNode }) {
  const demoUser = useSyncExternalStore(subscribe, readDemo, () => null);
  const hydrated = useSyncExternalStore(subscribe, () => true, () => false);
  const [user, setUser] = useState<SessionUser | null>(null);
  const [checked, setChecked] = useState(false);

  const fetchMe = useCallback(
    () => request<{ user: SessionUser }>("/api/auth/me").then((r) => r.user).catch(() => null),
    [],
  );

  useEffect(() => {
    let cancelled = false;
    fetchMe().then((u) => {
      if (cancelled) return;
      setUser(u);
      setChecked(true);
    });
    return () => { cancelled = true; };
  }, [fetchMe]);

  const setDemoUser = useCallback((id: string | null) => {
    try {
      if (id) localStorage.setItem(DEMO_KEY, id);
      else localStorage.removeItem(DEMO_KEY);
    } catch {}
    listeners.forEach((l) => l());
  }, []);

  const value = useMemo<Session>(() => ({
    ready: hydrated && checked,
    signedIn: Boolean(user) || Boolean(demoUser),
    user,
    demoUser,
    setDemoUser,
    refresh: async () => {
      const u = await fetchMe();
      setUser(u);
      return u;
    },
    signOut: async () => {
      setDemoUser(null);
      if (user) await request("/api/auth/logout", { method: "POST" }).catch(() => {});
      setUser(null);
    },
    // Real readers authenticate with the session cookie; demo readers with this header.
    headers: async (): Promise<Headers> => (demoUser ? { "X-Demo-User": demoUser } : {}),
  }), [hydrated, checked, user, demoUser, setDemoUser, fetchMe]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
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
