import { permanentRedirect } from "next/navigation";

// The canonical language-neutral URL resolves to the English public edition.
// A permanent redirect avoids a duplicate homepage while keeping installed
// ELYIO visits on /visit (manifest.json).
export default async function RootPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const query = await searchParams;
  const preserved = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    for (const item of Array.isArray(value) ? value : value ? [value] : []) preserved.append(key, item);
  }
  permanentRedirect(`/en${preserved.size ? `?${preserved.toString()}` : ""}`);
}
