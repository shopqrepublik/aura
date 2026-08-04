// Haptics per ELYIO-FINAL-PROMPT.md: "navigator.vibrate(10) soft impact on
// detect, 20 on shutter, light on segment switch, success on Add". Silently
// no-ops on browsers/devices without the Vibration API (desktop, iOS Safari)
// — this is a progressive-enhancement detail, not a required feature.
function vibrate(pattern: number | number[]) {
  if (typeof navigator !== "undefined" && "vibrate" in navigator) {
    try {
      navigator.vibrate(pattern);
    } catch {
      // ignore — vibration is best-effort
    }
  }
}

export const haptics = {
  detect: () => vibrate(10),
  shutter: () => vibrate(20),
  segmentSwitch: () => vibrate(6),
  success: () => vibrate([10, 30, 10]),
  // v3 "Curated Reveal": the single medium impact fired once, at the moment
  // a Major/Exceptional-tier Provenance Reveal settles on its full price
  // range (design-direction-v3.md §5). Standard-tier reveals fire nothing —
  // per the constitution's "no casino" rule, feedback intensity should
  // track how rare the moment actually is, not fire uniformly on every scan.
  impactMedium: () => vibrate(15),
};
