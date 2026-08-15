import { permanentRedirect } from "next/navigation";

// The canonical language-neutral URL resolves to the English public edition.
// A permanent redirect avoids a duplicate homepage while keeping installed
// ELYIO visits on /visit (manifest.json).
export default function RootPage() {
  permanentRedirect("/en");
}
