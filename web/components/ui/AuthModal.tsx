"use client";

import { useState } from "react";
import { ArrowRight } from "lucide-react";
import { tt } from "@/lib/i18n";
import type { Locale } from "@/lib/types";

const editorial = { fontFamily: "var(--font-editorial)" } as const;

// Real registration (email magic link + Google; Apple deferred until an
// Apple Developer account exists), shown on Home before "Begin your visit"
// is reachable -- same bottom-sheet material as MuseumSelectionSheet
// (HomeScreen.tsx) so this doesn't read as a bolted-on generic auth dialog.
export default function AuthModal({
  locale,
  onClose,
  signInWithEmail,
  signInWithGoogle,
}: {
  locale: Locale;
  onClose: () => void;
  signInWithEmail: (email: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
}) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [googleBusy, setGoogleBusy] = useState(false);

  async function handleSendLink(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || status === "sending") return;
    setStatus("sending");
    try {
      await signInWithEmail(email.trim());
      setStatus("sent");
    } catch {
      setStatus("error");
    }
  }

  async function handleGoogle() {
    setGoogleBusy(true);
    try {
      await signInWithGoogle();
      // Full-page redirect to Google follows -- this component unmounts,
      // no need to reset googleBusy on success.
    } catch {
      setGoogleBusy(false);
      setStatus("error");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40" />
      <div
        className="relative z-10 w-full rounded-t-[24px] bg-[#FDFBF7] p-6 pb-[max(28px,env(safe-area-inset-bottom))]"
        onClick={(e) => e.stopPropagation()}
      >
        {status === "sent" ? (
          <div className="text-center py-4">
            <div style={editorial} className="text-[24px] font-medium text-[#181714]">
              {tt("auth_check_email_title", locale)}
            </div>
            <p className="mt-3 text-[15px] leading-[21px] text-[#4F4C46]">
              {tt("auth_check_email_body", locale).replace("{email}", email.trim())}
            </p>
          </div>
        ) : (
          <>
            <div style={editorial} className="text-[24px] font-medium text-[#181714]">
              {tt("auth_modal_title", locale)}
            </div>
            <p className="mt-2 text-[14px] leading-[20px] text-[#67635C]">{tt("auth_modal_subtitle", locale)}</p>

            <form onSubmit={handleSendLink} className="mt-6">
              <label className="text-[10px] font-semibold tracking-[0.15em] uppercase text-[#67635C]">
                {tt("auth_email_label", locale)}
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                className="mt-2 w-full h-[50px] px-4 rounded-[12px] bg-white border border-[rgba(30,27,22,0.12)] text-[16px] text-[#181714] outline-none focus:border-[#181714]"
              />
              <button
                type="submit"
                disabled={status === "sending"}
                className="mt-3 w-full h-[54px] px-5 rounded-[14px] bg-[#181714] text-[#FAF6ED] flex items-center justify-between disabled:opacity-60"
              >
                <span className="text-[15px] font-medium tracking-[-0.01em]">{tt("auth_send_link", locale)}</span>
                <ArrowRight className="w-[16px] h-[16px]" />
              </button>
            </form>

            {status === "error" && (
              <p className="mt-2 text-[12px] text-[#A83A3A]">{tt("auth_error_generic", locale)}</p>
            )}

            <div className="mt-5 flex items-center gap-3">
              <div className="flex-1 h-px bg-[rgba(30,27,22,0.09)]" />
              <span className="text-[11px] font-medium uppercase tracking-[0.1em] text-[#8B867E]">
                {tt("auth_or_divider", locale)}
              </span>
              <div className="flex-1 h-px bg-[rgba(30,27,22,0.09)]" />
            </div>

            <button
              type="button"
              onClick={handleGoogle}
              disabled={googleBusy}
              className="mt-5 w-full h-[54px] rounded-[14px] border border-[rgba(30,27,22,0.14)] bg-white text-[#181714] text-[15px] font-medium disabled:opacity-60"
            >
              {tt("auth_continue_google", locale)}
            </button>

            <button
              type="button"
              onClick={onClose}
              className="mt-4 w-full text-center text-[13px] font-medium text-[#8B867E]"
            >
              {tt("auth_close", locale)}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
