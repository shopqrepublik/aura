import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const files = [
  "lib/app-state.ts",
  "components/screens/UncatalogedCardScreen.tsx",
  "lib/i18n.ts",
  "lib/generated-enrichment.ts",
].map((file) => path.join(root, file));

const forbiddenRuntimePhrases = [
  "ELYIO has not reviewed",
  "not yet one of our reviewed catalog records",
  "recognition is strong enough",
  "curated catalog record",
  "database incomplete",
  "Layer 1",
  "Layer 2",
  "source_ids",
];

let failed = false;
for (const file of files) {
  const rel = path.relative(root, file);
  let text = fs.readFileSync(file, "utf8");
  if (rel.replaceAll("\\", "/") === "lib/generated-enrichment.ts") {
    text = text.replace(/const FORBIDDEN_VISITOR_TERMS = \[[\s\S]*?\];/, "");
  }
  for (const phrase of forbiddenRuntimePhrases) {
    if (text.includes(phrase)) {
      console.error(`[generated-enrichment-regression] Forbidden visitor phrase found in ${rel}: ${phrase}`);
      failed = true;
    }
  }
}

const enrichment = fs.readFileSync(path.join(root, "lib/generated-enrichment.ts"), "utf8");
for (const required of ["titian_mirror", "van_gogh_self_portrait", "antonello_ecce_homo", "ARTIST_MARKET_CONTEXT", "NO_TRUSTED_CONTEXT"]) {
  if (!enrichment.includes(required)) {
    console.error(`[generated-enrichment-regression] Missing required generated-result branch: ${required}`);
    failed = true;
  }
}

if (failed) process.exit(1);
console.log("[generated-enrichment-regression] PASS");
