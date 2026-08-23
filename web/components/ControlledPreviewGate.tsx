"use client";

import { FormEvent, ReactNode, useEffect, useState } from "react";
import { getMuseums } from "@/lib/api";

const QA_TOKEN_KEY = "elyio-trusted-qa-token";

export default function ControlledPreviewGate({ enabled, children }: { enabled: boolean; children: ReactNode }) {
  const [ready, setReady] = useState(!enabled);
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    if (!enabled || !window.sessionStorage.getItem(QA_TOKEN_KEY)) return;
    const pending = window.setTimeout(() => setReady(true), 0);
    return () => window.clearTimeout(pending);
  }, [enabled]);

  if (ready) return children;

  async function unlock(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = token.trim();
    if (!value) return;
    setChecking(true);
    setError("");
    window.sessionStorage.setItem(QA_TOKEN_KEY, value);
    try {
      const museums = await getMuseums({ q: "National Gallery", limit: 20 });
      if (!museums.some((museum) => museum.id === "national-gallery-london")) throw new Error("not authorized");
      setToken("");
      setReady(true);
    } catch {
      window.sessionStorage.removeItem(QA_TOKEN_KEY);
      setError("Access was not authorized. Check the QA token and try again.");
    } finally {
      setChecking(false);
    }
  }

  return (
    <main className="min-h-dvh bg-[#F7F3EC] px-6 py-16 text-[#171512]">
      <form onSubmit={unlock} className="mx-auto max-w-sm rounded-2xl border border-black/10 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-black/50">ELYIO controlled preview</p>
        <h1 className="mt-3 text-2xl font-semibold">Authorized tester access</h1>
        <p className="mt-3 text-sm leading-6 text-black/65">
          Enter the internal QA token supplied by the ELYIO operator. It is kept only in this browser tab.
        </p>
        <label className="mt-6 block text-sm font-medium" htmlFor="elyio-qa-token">QA token</label>
        <input
          id="elyio-qa-token"
          type="password"
          autoComplete="off"
          value={token}
          onChange={(event) => setToken(event.target.value)}
          className="mt-2 w-full rounded-xl border border-black/20 bg-white px-4 py-3"
        />
        {error ? <p role="alert" className="mt-3 text-sm text-red-700">{error}</p> : null}
        <button disabled={checking} type="submit" className="mt-4 w-full rounded-xl bg-[#171512] px-4 py-3 font-medium text-white disabled:opacity-50">
          {checking ? "Checking access…" : "Open controlled preview"}
        </button>
      </form>
    </main>
  );
}
