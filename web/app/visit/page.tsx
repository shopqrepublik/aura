import type { Metadata } from "next";
import ElyioApp from "@/components/ElyioApp";
import ControlledPreviewGate from "@/components/ControlledPreviewGate";

export const metadata: Metadata = {
  title: "Start your ELYIO museum visit",
  description: "Open the ELYIO camera guide and begin your museum visit.",
  robots: { index: false, follow: false },
  alternates: { canonical: "https://www.elyio.co/visit" },
};

export default async function VisitPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const query = await searchParams;
  const first = (value: string | string[] | undefined) => Array.isArray(value) ? value[0] : value;
  const controlledPreview = first(query["controlled-preview"]) === "1";
  const requestedLocale = first(query.locale)?.toLowerCase();
  const locale = requestedLocale === "fr" || requestedLocale === "zh-hans" ? requestedLocale : requestedLocale === "en" ? "en" : undefined;
  return (
    <ControlledPreviewGate enabled={controlledPreview}>
      <ElyioApp directToScanner initialLocale={locale === "zh-hans" ? "zh-Hans" : locale} />
    </ControlledPreviewGate>
  );
}
