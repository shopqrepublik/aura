// Musée d'Orsay is the only museum ELYIO covers today, so this stays a flat
// export rather than a per-museum theme lookup table -- that structure (see
// desktop-rebuild spec §83-85: museum.theme.backgroundAsset etc.) is worth
// building once a second museum actually exists, not before.
//
// Shared between HomeScreen.tsx (mobile hero background) and the desktop
// shell's atmospheric clock backdrop -- both need the exact same source
// image. Real photo (Roman Eisele, Wikimedia Commons, CC BY-SA 4.0);
// original is 3072x2048 (3:2), confirmed directly against Wikimedia's API
// rather than assumed. Served through backend/app/main.py's /v1/image-proxy
// (proxyImageUrl in ./visitPalette), which now accepts a `width` query
// param -- callers needing a larger render (e.g. the desktop backdrop) pass
// one instead of duplicating this URL with a different resize path.
export const ORSAY_CLOCK_IMAGE_URL =
  "http://commons.wikimedia.org/wiki/Special:FilePath/Paris%20-%20Mus%C3%A9e%20d'Orsay%20-%20big%20clock%20seen%20from%20the%20interior.jpg";
