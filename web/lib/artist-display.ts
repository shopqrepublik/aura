import { tt } from "./i18n";
import type { Artwork, Locale } from "./types";

export function artistDisplayName(artist: string | null | undefined, locale: Locale): string {
  return artist || tt("uncataloged_unknown_artist", locale);
}

export function artworkArtistDisplayName(artwork: Artwork, locale: Locale): string {
  return artistDisplayName(artwork.artist, locale);
}
