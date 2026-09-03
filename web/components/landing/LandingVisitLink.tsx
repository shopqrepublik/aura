"use client";

import { useRef } from "react";
import Link from "next/link";
import { trackGoogleEvent } from "@/lib/analytics";
import type { MouseEvent, PointerEvent, ReactNode } from "react";

type TrackedNativeEvent = Event & { __elyioBeginVisitTracked?: boolean };

function localeFromHref(href: string) {
  try {
    return new URL(href, window.location.href).searchParams.get("locale") || "en";
  } catch {
    return "en";
  }
}

export default function LandingVisitLink({
  className,
  href,
  sourceSurface,
  children,
}: {
  className: string;
  href: string;
  sourceSurface: "landing_header" | "landing_hero" | "landing_footer";
  children: ReactNode;
}) {
  const pointerTracked = useRef(false);

  const trackBeginVisit = (event: MouseEvent<HTMLAnchorElement> | PointerEvent<HTMLAnchorElement>) => {
    const nativeEvent = event.nativeEvent as TrackedNativeEvent;
    if (nativeEvent.__elyioBeginVisitTracked) return;
    nativeEvent.__elyioBeginVisitTracked = true;
    trackGoogleEvent("begin_visit", {
      locale: localeFromHref(event.currentTarget.href),
      source_surface: sourceSurface,
    });
  };

  const handlePointerDown = (event: PointerEvent<HTMLAnchorElement>) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    pointerTracked.current = true;
    trackBeginVisit(event);
  };

  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
    if (pointerTracked.current) {
      pointerTracked.current = false;
      (event.nativeEvent as TrackedNativeEvent).__elyioBeginVisitTracked = true;
    } else {
      trackBeginVisit(event);
    }
    const target = event.currentTarget.href;
    const before = window.location.href;
    window.setTimeout(() => {
      if (window.location.href === before) window.location.assign(target);
    }, 700);
  };

  return (
    <Link className={className} href={href} data-ga-begin-visit={sourceSurface} onPointerDown={handlePointerDown} onClick={handleClick}>
      {children}
    </Link>
  );
}
