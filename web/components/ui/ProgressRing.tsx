// SVG progress ring — one component, two sizes in the spec:
//   - mission cards: 32x32, r=13, stroke 3, track #E5E5EA, progress #111
//   - progress-screen stat ring: 32x32 viewBox but rendered 16x16/64x64
//     container, r=26, stroke 4 (dasharray "45 163" in the reference demo
//     was a hardcoded 28%; here it's computed from real `progress`)
export default function ProgressRing({
  progress, // 0..1
  radius,
  strokeWidth,
  size,
  trackColor = "#E5E5EA",
  progressColor = "#111111",
  centerLabel,
}: {
  progress: number;
  radius: number;
  strokeWidth: number;
  size: number;
  trackColor?: string;
  progressColor?: string;
  centerLabel?: React.ReactNode;
}) {
  const clamped = Math.max(0, Math.min(1, progress));
  const circumference = 2 * Math.PI * radius;
  const viewBox = radius * 2 + strokeWidth * 2;
  const center = viewBox / 2;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${viewBox} ${viewBox}`}
        className="-rotate-90"
      >
        <circle cx={center} cy={center} r={radius} fill="none" stroke={trackColor} strokeWidth={strokeWidth} />
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={progressColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${clamped * circumference} ${circumference}`}
        />
      </svg>
      {centerLabel != null && (
        <div className="absolute inset-0 flex items-center justify-center text-[10px] font-bold">
          {centerLabel}
        </div>
      )}
    </div>
  );
}
