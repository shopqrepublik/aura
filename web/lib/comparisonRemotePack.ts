import { COMPARISON_V22_REMOTE_IDS, productionEligibleReferences, type V22Catalog } from "./comparisonEngineV22";

const CACHE_KEY = "elyio-comparison-v22-remote-lkg";
const ALLOWED_IDS = new Set<string>(COMPARISON_V22_REMOTE_IDS);

export interface RemotePack extends V22Catalog {
  pack_id: string;
  expires_at: string;
  source_required: boolean;
  allowlist: boolean;
}

export function validateRemotePack(value: unknown, now = new Date()): { valid: boolean; errors: string[]; pack?: RemotePack } {
  const errors: string[] = [];
  if (!value || typeof value !== "object") return { valid: false, errors: ["schema"] };
  const pack = value as RemotePack;
  if (pack.version !== "1.0" || pack.schema_version !== "2.2" || !pack.pack_id || !Array.isArray(pack.comparisons)) errors.push("version_or_schema");
  if (pack.allowlist !== true || pack.source_required !== true) errors.push("policy");
  const expiry = Date.parse(pack.expires_at);
  if (!Number.isFinite(expiry) || expiry < now.getTime()) errors.push("expired_pack");
  if (pack.comparisons.length !== ALLOWED_IDS.size || pack.comparisons.some((item) => !ALLOWED_IDS.has(item.id))) errors.push("allowlist");
  if (new Set(pack.comparisons.map((item) => item.id)).size !== pack.comparisons.length) errors.push("duplicate_id");
  if (productionEligibleReferences(pack, now).length !== pack.comparisons.length) errors.push("invalid_reference");
  return { valid: errors.length === 0, errors: [...new Set(errors)], ...(errors.length ? {} : { pack }) };
}

export async function loadRemotePack(options: { url?: string; disabled?: boolean; now?: Date } = {}): Promise<RemotePack | null> {
  if (options.disabled || !options.url || typeof window === "undefined") return null;
  const now = options.now || new Date();
  try {
    const response = await fetch(options.url, { headers: { Accept: "application/json" }, cache: "no-store" });
    if (!response.ok) throw new Error(`remote pack HTTP ${response.status}`);
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.toLowerCase().includes("application/json")) throw new Error("remote pack is not JSON");
    const result = validateRemotePack(await response.json(), now);
    if (!result.valid || !result.pack) throw new Error(`invalid remote pack: ${result.errors.join(",")}`);
    try { window.localStorage.setItem(CACHE_KEY, JSON.stringify(result.pack)); } catch { /* cache is optional */ }
    return result.pack;
  } catch {
    try {
      const cached = JSON.parse(window.localStorage.getItem(CACHE_KEY) || "null") as unknown;
      const result = validateRemotePack(cached, now);
      return result.valid ? result.pack || null : null;
    } catch { return null; }
  }
}
