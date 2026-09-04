import { NextResponse } from "next/server";
import { LOCALES } from "@/lib/seo-content";

export function GET(_request: Request, { params }: { params: Promise<{ locale: string }> }) {
  return params.then(({ locale }) => {
    if (!LOCALES.includes(locale as (typeof LOCALES)[number])) return new NextResponse("Not found", { status: 404 });
    const language = locale === "zh-hans" ? "简体中文" : locale === "fr" ? "Français" : "English";
    return NextResponse.json({ name: "ELYIO", short_name: "ELYIO", description: "ELYIO AI museum companion", start_url: `/${locale}`, scope: "/", display: "standalone", orientation: "portrait", background_color: "#FAFAF9", theme_color: "#FAFAF9", lang: language, icons: [{ src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" }, { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" }, { src: "/icons/icon-192-maskable.png", sizes: "192x192", type: "image/png", purpose: "maskable" }, { src: "/icons/icon-512-maskable.png", sizes: "512x512", type: "image/png", purpose: "maskable" }] });
  });
}
