import { NextResponse, type NextRequest } from "next/server";

// Preserve the canonical apex redirect while allowing Android's Digital Asset
// Links endpoint to return a direct 200 response on both claimed hosts.
export function proxy(request: NextRequest) {
  const host = request.headers.get("host")?.split(":")[0].toLowerCase();
  if (host === "elyio.co" && request.nextUrl.pathname !== "/.well-known/assetlinks.json") {
    return NextResponse.redirect(new URL(`https://www.elyio.co${request.nextUrl.pathname}${request.nextUrl.search}`, request.url), 308);
  }
  return NextResponse.next();
}

export const config = { matcher: "/:path*" };
