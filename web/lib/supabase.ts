import { createClient } from "@supabase/supabase-js";

// Plain browser client -- this app's entire architecture is client-side
// state (useElyioApp, "use client" everywhere, no Next.js server
// components/route handlers in the auth path), so there's no server-side
// session to keep in sync via cookies/middleware. supabase-js's default
// localStorage persistence + auto token refresh already satisfies "don't
// ask to log in again on every open" (§3 session requirement) on its own.
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// createClient() throws SYNCHRONOUSLY on an empty URL -- and this module is
// imported by lib/api.ts, itself imported by nearly every screen (via
// app-state.ts). Without the fallback below, deploying this before Vercel's
// NEXT_PUBLIC_SUPABASE_* env vars are actually set would crash the entire
// app at load time (white screen), not just the new auth feature. A
// syntactically-valid placeholder keeps the app itself loading; only real
// sign-in attempts against it fail (caught in useAuth.ts's try/catch).
export const supabase = createClient(
  SUPABASE_URL || "https://placeholder.supabase.co",
  SUPABASE_ANON_KEY || "placeholder-anon-key"
);
