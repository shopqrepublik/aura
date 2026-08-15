import type { Metadata } from "next";
import ElyioApp from "@/components/ElyioApp";

export const metadata: Metadata = {
  title: "Start your ELYIO museum visit",
  description: "Open the ELYIO camera guide and begin your museum visit.",
  robots: { index: false, follow: false },
  alternates: { canonical: "https://www.elyio.co/visit" },
};

export default function VisitPage() {
  return <ElyioApp />;
}
