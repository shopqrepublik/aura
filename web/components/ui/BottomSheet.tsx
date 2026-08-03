"use client";

import { useEffect } from "react";

// "Bottom sheet: 0 16px 32px rgba(0,0,0,0.22)" + "Spring: card open spring(0.8)
// translateY from bottom" — approximated with a CSS transition since a real
// spring needs a JS animation library we don't otherwise need here.
export default function BottomSheet({
  open,
  onClose,
  children,
}: {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <div
      className={`fixed inset-0 z-50 flex items-end justify-center transition-opacity duration-300 ${
        open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"
      }`}
      aria-hidden={!open}
    >
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div
        className={`relative w-full max-w-[420px] bg-white rounded-t-[24px] shadow-[0_16px_32px_rgba(0,0,0,0.22)] p-6 pb-8 transition-transform duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] ${
          open ? "translate-y-0" : "translate-y-full"
        }`}
      >
        <div className="mx-auto mb-5 w-10 h-1 rounded-full bg-black/15" />
        {children}
      </div>
    </div>
  );
}
