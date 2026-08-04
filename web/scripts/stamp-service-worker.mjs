// Generates public/sw.js from sw-template.js, stamping a fresh
// CACHE_VERSION on every run. Wired as `prebuild`/`predev` in package.json
// so npm runs it automatically before every dev/build -- public/sw.js
// itself is gitignored (a generated artifact), so this file's bytes
// change on every build without ever leaving public/sw.js "dirty" in git.
//
// This is the actual fix for stale-PWA staleness: browsers only re-run a
// service worker's install/activate cycle when the SW script's BYTES
// change. sw-template.js's caching logic rarely changes, but app content
// (prices, mission text, catalog data) changes on almost every deploy and
// is baked into the JS bundle, not the SW file -- without a version stamp
// forcing public/sw.js's bytes to differ every build, the browser never
// notices anything changed, and an already-open tab or installed PWA can
// stay on a months-old cached page indefinitely.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const templatePath = join(__dirname, "..", "sw-template.js");
const outPath = join(__dirname, "..", "public", "sw.js");

const version = Date.now().toString(36);
const template = readFileSync(templatePath, "utf8");
const stamped = template.replace('const CACHE_VERSION = "__SW_VERSION__";', `const CACHE_VERSION = "${version}";`);

if (stamped === template) {
  throw new Error(`stamp-service-worker: __SW_VERSION__ placeholder not found in ${templatePath}`);
}

writeFileSync(outPath, stamped, "utf8");
console.log(`stamp-service-worker: generated public/sw.js (CACHE_VERSION=${version})`);
