"use client";

import { useEffect, useRef, useState } from "react";

// Registers sw.js scoped to "/" — the real app now lives at the root route
// (app/page.tsx), so the installed PWA experience covers the whole origin;
// /design (the dev-facing design system) is technically in scope too, but
// nothing in the app links to it, so no real visitor ever lands there.
//
// Also surfaces a minimal "Update available" banner, using the standard
// waiting-worker handoff: sw-template.js's installed worker deliberately
// does NOT call self.skipWaiting() on its own anymore (see that file's own
// comment) -- it parks in the "waiting" state until this component posts
// it a SKIP_WAITING message, which only happens when a visitor taps this
// banner. That's what makes the swap non-disruptive: nothing about the
// active tab changes on its own mid-visit, no matter how long a museum
// session runs. Kept deliberately simple (fixed English copy, no i18n)
// since this renders in the root layout, outside the app's own locale
// state (lib/app-state.ts), and this is a rare, non-critical system-level
// notice, not app content.
//
// register() only checks for an update at the moment it runs, i.e. once
// per real page execution. That's not enough on iOS: a backgrounded
// installed PWA is typically suspended in memory rather than closed, and
// reopening it (app switcher / home-screen icon, short of a force-quit)
// often resumes the exact same JS context with no navigation and no
// re-run of this effect — so the app can go a very long time without ever
// re-checking. visibilitychange/pageshow/focus are the signals that DO
// fire when a suspended page resumes, so an explicit update() call on each
// makes the check happen every time the user actually looks at the app
// again, instead of depending on a fresh full reload the platform may
// never deliver on its own.
export default function ServiceWorkerRegister() {
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const waitingWorkerRef = useRef<ServiceWorker | null>(null);

  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    let registration: ServiceWorkerRegistration | null = null;
    let reloaded = false;

    const armWaitingWorker = (worker: ServiceWorker | null) => {
      if (!worker) return;
      waitingWorkerRef.current = worker;
      setUpdateAvailable(true);
    };

    // Shared by both call sites below: an install already in flight when
    // this component mounts (caught via reg.installing directly) and one
    // that starts later (caught via "updatefound"). Watching only
    // "updatefound" has a real gap -- if an update began (another tab
    // called update(), or the browser's own periodic check fired) in the
    // window between register()'s promise resolving and this listener
    // being attached, that specific install's "updatefound" has already
    // fired and is gone; reg.installing is still readable at that point,
    // so checking it directly on mount catches exactly that race.
    const watchInstalling = (installing: ServiceWorker | null) => {
      if (!installing) return;
      installing.addEventListener("statechange", () => {
        // "installed" with an existing controller means a NEW version
        // finished installing behind the currently-active one -- not
        // the very first-ever install (which also passes through
        // "installed" but there's no controller yet to hand off from).
        if (installing.state === "installed" && navigator.serviceWorker.controller) {
          armWaitingWorker(installing);
        }
      });
    };

    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then((reg) => {
        registration = reg;
        // A worker can already be sitting fully in "waiting" if this tab
        // was reopened after a background update finished installing while
        // it was closed (or backgrounded on iOS -- see this file's own
        // top-level comment), and one can already be mid-"installing" if an
        // update started moments before this tab loaded -- cover both.
        armWaitingWorker(reg.waiting);
        watchInstalling(reg.installing);
        reg.addEventListener("updatefound", () => {
          watchInstalling(reg.installing);
        });
      })
      .catch(() => {
        // registration is a progressive enhancement — the app works fine without it
      });

    // "controllerchange" fires whenever the page's controller goes from
    // null to a worker, NOT only when an existing controller is replaced --
    // clients.claim() on this page's own very first activation (no prior
    // controller to protect, so the browser skips "waiting" and activates
    // immediately even without skipWaiting()) fires it too. Without this
    // guard, a fresh tab with no controller yet reloads the instant its own
    // first SW claims it, the reloaded page has no controller AGAIN for a
    // moment before the same claim repeats, and it never stops -- caught
    // live during testing as a genuine infinite reload loop. Only a
    // controllerchange with an ALREADY-existing controller beforehand is a
    // real hand-off (which, in this design, only ever happens via the
    // "Refresh" button's SKIP_WAITING message -- see this file's own
    // top-level comment), so only that case should reload.
    let hadController = !!navigator.serviceWorker.controller;
    const onControllerChange = () => {
      if (!hadController) {
        hadController = true;
        return;
      }
      if (reloaded) return;
      reloaded = true;
      window.location.reload();
    };
    navigator.serviceWorker.addEventListener("controllerchange", onControllerChange);

    // pageshow fires almost immediately on every fresh load, effectively
    // duplicating register()'s OWN initial install/claim -- calling
    // update() while that first install is still in flight is a plausible
    // race with it (a second, spurious controllerchange landing after
    // hadController has already flipped true from the legitimate first
    // claim would read as a real hand-off and reload). Not confirmed as
    // the cause of any specific observed bug, but there's no upside to
    // calling update() before the page even has a controller to check
    // freshness against, so this closes the race defensively at zero
    // cost: no-ops on that first load, only does real work on later,
    // genuine visibility/focus events.
    const checkForUpdate = () => {
      if (!navigator.serviceWorker.controller) return;
      registration?.update().catch(() => {});
    };
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") checkForUpdate();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    window.addEventListener("pageshow", checkForUpdate);
    window.addEventListener("focus", checkForUpdate);

    return () => {
      navigator.serviceWorker.removeEventListener("controllerchange", onControllerChange);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("pageshow", checkForUpdate);
      window.removeEventListener("focus", checkForUpdate);
    };
  }, []);

  if (!updateAvailable) return null;

  return (
    <button
      type="button"
      onClick={() => waitingWorkerRef.current?.postMessage("SKIP_WAITING")}
      className="fixed top-3 left-1/2 -translate-x-1/2 z-[999] h-[36px] px-4 rounded-full bg-black text-white text-[13px] font-semibold shadow-[0_8px_24px_rgba(0,0,0,0.3)] active:scale-[0.98] transition-transform"
    >
      Update available · Tap to refresh
    </button>
  );
}
