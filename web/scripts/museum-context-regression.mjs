import assert from "node:assert/strict";
import fs from "node:fs";

// This is intentionally a focused source contract test for the async museum
// race fixed in 5523cf7. Recognition callbacks may outlive the render that
// created them, so every scan must read the latest authoritative ref.
const source = fs.readFileSync(new URL("../lib/app-state.ts", import.meta.url), "utf8");
assert.match(source, /const museumContextRef = useRef/);
assert.match(source, /museumContextRef\.current = \{ id: state\.museumId/);
assert.match(source, /const latestMuseum = museumContextRef\.current/);
assert.match(source, /api\.recognize\(\s*\n\s*imageBase64,\s*\n\s*state\.locale,\s*\n\s*latestMuseum\.id/);
assert.doesNotMatch(source, /api\.recognize\(\s*\n\s*imageBase64,\s*\n\s*state\.locale,\s*\n\s*state\.museumId/);

const apiSource = fs.readFileSync(new URL("../lib/api.ts", import.meta.url), "utf8");
assert.match(apiSource, /\.\.\.\(museumId \? \{ museum_id: museumId \} : \{\}\)/);

console.log("museum-context-regression: PASS (latest museum ref, no stale closure, empty string omitted)");
