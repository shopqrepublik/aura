"use client";

import { useEffect, useRef, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./supabase";
import { setAnalyticsAuthToken, track } from "./analytics";

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
  // Supabase's implicit OAuth/magic-link flow completing on this page can
  // emit more than one "SIGNED_IN" event for the same login (observed live:
  // 3 for one Google sign-in) -- this guards onboarding_completed to fire
  // at most once per page load rather than trusting SIGNED_IN's count.
  const onboardingTrackedRef = useRef(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setAnalyticsAuthToken(data.session?.access_token);
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
      setAnalyticsAuthToken(newSession?.access_token);
      setSession(newSession);
      if (event === "SIGNED_IN" && newSession) {
        // Strip a magic-link/OAuth hash (#access_token=...&...) from the URL
        // bar right here, inside the SIGNED_IN handler -- this event only
        // fires once supabase-js has already parsed the hash itself, so
        // there's no race with its own internal read of it (stripping any
        // earlier risks deleting the hash before the SDK gets to read it).
        // Caught live: PostHog was capturing $current_url with the raw
        // access_token still in it, because track() below read
        // window.location before this cleanup existed.
        if (typeof window !== "undefined" && window.location.hash.includes("access_token")) {
          window.history.replaceState(null, "", window.location.pathname + window.location.search);
        }
        if (!onboardingTrackedRef.current) {
          onboardingTrackedRef.current = true;
          track("onboarding_completed", { auth_provider: newSession.user.app_metadata?.provider ?? "email" });
        }
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
