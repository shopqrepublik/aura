import type { Metadata, Viewport } from "next";
import { Cormorant_Garamond } from "next/font/google";
import "./globals.css";
import "../components/landing/landing.css";
import GoogleAnalytics from "@/components/GoogleAnalytics";

// Editorial serif for artwork titles / Reveal price / Recap value -- next/font
// self-hosts the font files at build time (no runtime request to Google's
// CDN), so this doesn't add an external dependency or a CSP concern for the
// PWA. Only the CJK-less latin(-ext) subsets are needed: the font falls
// through to the system serif in the stack for zh-Hans text, same as any
// other font missing those glyphs.
const editorialSerif = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-editorial",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://www.elyio.co"),
  title: "ELYIO — AI Museum Guide for Art & Museums",
  description: "Point your camera at an artwork and ELYIO helps you recognize it, understand the story behind it, and explore museums from Paris to New York and beyond.",
  manifest: "/manifest.json",
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: "/icons/icon-192.png",
  },
  appleWebApp: {
    capable: true,
    title: "ELYIO",
    statusBarStyle: "default",
  },
  // The app switches locale client-side (no server-rendered lang routing),
  // so <html lang> below can't track it and Chrome's translate heuristic
  // sees a mismatch against the real French/Chinese UI text and offers to
  // "helpfully" machine-translate over our authored i18n copy. notranslate
  // opts out for every locale, not just during testing.
  other: {
    google: "notranslate",
    "apple-mobile-web-app-capable": "yes",
    "robots": "index, follow, max-image-preview:large",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#FAFAF9",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" translate="no" className={`h-full antialiased ${editorialSerif.variable}`}>
      <body className="min-h-full flex flex-col bg-[#F7F3EC] text-[#181714]">
        {children}
        <GoogleAnalytics />
      </body>
    </html>
  );
}
