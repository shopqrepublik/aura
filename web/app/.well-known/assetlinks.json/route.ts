import { NextResponse } from "next/server";

// The certificate fingerprint is deployment configuration because the Play
// app-signing certificate does not exist until the Android identity is set up.
// Never put a private key or upload-key password in this response.
export function GET() {
  const packageName = process.env.ANDROID_APPLICATION_ID || "co.elyio.app";
  const fingerprints = (process.env.ANDROID_ASSETLINKS_SHA256 || "")
    .split(",")
    .map((value) => value.trim().toUpperCase())
    .filter(Boolean);
  return NextResponse.json(fingerprints.length ? [{ relation: ["delegate_permission/common.handle_all_urls"], target: { namespace: "android_app", package_name: packageName, sha256_cert_fingerprints: fingerprints } }] : []);
}
