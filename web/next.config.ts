import type { NextConfig } from "next";

// Real origins this app actually talks to (verified live against prod, not
// guessed): backend API (lib/api.ts's BACKEND_URL), Supabase auth
// (lib/supabase.ts), PostHog (lib/analytics.ts -- both us./eu.i.posthog.com
// listed because NEXT_PUBLIC_POSTHOG_HOST determines which one is live and
// this must not silently break if that value changes; us-assets/eu-assets
// are where posthog-js fetches its remote config), and Wikimedia --
// most artwork photos are proxied through our own /v1/image-proxy, but
// CardScreen/RecapScreen/ProgressScreen's on-screen (non-canvas) <img> tags
// hotlink artwork.imageUrl directly (only the canvas-export path needs the
// CORS-enabled proxy), so Wikimedia itself must stay allowed or those break.
const BACKEND_ORIGIN = "https://api.elyio.co";
const SUPABASE_ORIGIN = "https://smjvufoavwmenodxcmlg.supabase.co";

// 'unsafe-inline' on script-src/style-src: Next.js's own hydration payload
// is an inline <script> tag (not a src=), and this app's components lean
// heavily on React's style={{}} prop -- a real nonce-based CSP is the
// stricter follow-up, but that needs per-request middleware wiring, and the
// ask here is a starter policy that doesn't break the app today.
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' https://us-assets.i.posthog.com https://eu-assets.i.posthog.com",
  "style-src 'self' 'unsafe-inline'",
  `img-src 'self' data: ${BACKEND_ORIGIN} https://*.wikimedia.org`,
  "font-src 'self' data:",
  `connect-src 'self' ${BACKEND_ORIGIN} ${SUPABASE_ORIGIN} https://us.i.posthog.com https://eu.i.posthog.com https://us-assets.i.posthog.com https://eu-assets.i.posthog.com`,
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "upgrade-insecure-requests",
].join("; ");

const nextConfig: NextConfig = {
  images: {
    formats: ["image/avif", "image/webp"],
    remotePatterns: [{ protocol: "https", hostname: "api.elyio.co", pathname: "/v1/image-proxy" }],
    minimumCacheTTL: 31536000,
  },
  async headers() {
    return [
      {
        source: "/design",
        headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }],
      },
      {
        source: "/louvre-golden20-preview",
        headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }],
      },
      {
        source: "/visit",
        headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }],
      },
      {
        source: "/(.*)",
        headers: [
          { key: "Content-Security-Policy", value: CSP },
          // Belt-and-suspenders with frame-ancestors above -- CSP3 is the
          // modern directive, XFO is what every browser has honored for
          // over a decade, no reason to drop it.
          { key: "X-Frame-Options", value: "DENY" },
          // Safe here specifically because this app never opens a popup
          // (no window.open/target=_blank anywhere) -- Supabase's Google
          // OAuth is a full top-level redirect, not a popup, so COOP
          // isolating the browsing context group doesn't touch it.
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
          { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          ...(process.env.VERCEL_ENV && process.env.VERCEL_ENV !== "production"
            ? [{ key: "X-Robots-Tag", value: "noindex, nofollow" }]
            : []),
        ],
      },
    ];
  },
  async redirects() {
    return [
      { source: "/:path*", has: [{ type: "host", value: "elyio.co" }], destination: "https://www.elyio.co/:path*", permanent: true },
    ];
  },
};

export default nextConfig;
