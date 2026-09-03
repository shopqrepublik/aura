import type { Metadata } from "next";
import ElyioApp from "@/components/ElyioApp";
import ControlledPreviewGate from "@/components/ControlledPreviewGate";

export const metadata: Metadata = {
  title: "Start your ELYIO museum visit",
  description: "Open the ELYIO camera guide and begin your museum visit.",
  robots: { index: false, follow: false },
  alternates: { canonical: "https://www.elyio.co/visit" },
};

export default async function VisitPage({ searchParams }: { searchParams: Promise<{ "controlled-preview"?: string }> }) {
  const query = await searchParams;
  const controlledPreview = query["controlled-preview"] === "1";
  return <ControlledPreviewGate enabled={controlledPreview}><ElyioApp /></ControlledPreviewGate>;
}
