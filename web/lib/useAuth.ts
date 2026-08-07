"use client";

import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./supabase";
import { track } from "./analytics";

// Real registration (email magic link + Google; Apple deferred until an
// Apple Developer account exists) -- separate from useElyioApp's
// screen/visit state machine on purpose: auth is a session that outlives
// any single visit, not something that resets on newVisit().
export function useAuth() {
  const [session, setSession] = useState<Session | null>(null);
  // Starts true on both server and client (no branching on
  // typeof window here) so the first client render matches SSR -- same
  // hydration-mismatch avoidance as useMuseumDetection's "checking" state.
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });
    // Fires on sign-in (including the magic-link/Google redirect completing),
    // sign-out, and token refresh -- this is what makes "don't ask to log in
    // again" work: supabase-js persists + auto-refreshes the session in
    // localStorage on its own, this listener just keeps React in sync.
    //
    // onboarding_completed (§13): there's no separate tutorial/onboarding
    // screen in this app (Home + language picker + sign-in *is* the whole
    // first-run flow), so this fires on the "SIGNED_IN" event specifically
    // -- a real completed sign-in (magic-link/Google redirect finishing) --
    // not on "INITIAL_SESSION" (an existing session merely being restored on
    // page load), which is what makes this a one-time-per-registration
    // signal rather than firing on every return visit.
    const { data: listener } = supabase.auth.onAuthStateChange((event, newSession) => {
      setSession(newSession);
      if (event === "SIGNED_IN" && newSession) {
        track("onboarding_completed", { auth_provider: newSession.user.app_metadata?.provider ?? "email" });
      }
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  async function signInWithEmail(email: string): Promise<void> {
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: typeof window !== "undefined" ? window.location.origin : undefined },
    });
    if (error) throw error;
  }

  async function signInWithGoogle(): Promise<void> {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: typeof window !== "undefined" ? window.location.origin : undefined },
    });
    if (error) throw error;
  }

  return {
    session,
    user: session?.user ?? null,
    loading,
    signInWithEmail,
    signInWithGoogle,
  };
}
