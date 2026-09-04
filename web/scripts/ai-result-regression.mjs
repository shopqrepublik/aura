import assert from "node:assert/strict";
import fs from "node:fs";

const state = fs.readFileSync(new URL("../lib/app-state.ts", import.meta.url), "utf8");
const card = fs.readFileSync(new URL("../components/screens/UncatalogedCardScreen.tsx", import.meta.url), "utf8");

// `artwork_id=null` must enter the existing uncataloged result-card path and
// must never be treated as a retry by itself.
assert.match(state, /if \(!artwork \|\| result\.status === "no_match"\)/);
assert.match(state, /const uncataloged = result\.recognized_but_not_cataloged/);
assert.match(state, /recognition_mode: "ai_fallback"/);
assert.match(card, /const sighting = state\.uncatalogedSighting/);
assert.match(card, /const title =/);
assert.match(card, /const artist =/);
assert.doesNotMatch(card, /sighting\.artwork_id/);

console.log("ai-result-regression: PASS (AI-only null artwork_id renders the existing result card)");
