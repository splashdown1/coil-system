import type { Context } from "hono";
import { readFileSync, readdirSync } from "fs";
import { join } from "path";
const MANIFESTS_DIR = "/home/workspace/manifests";
const CANONICAL_ARTIFACTS = ["COIL_MASTER_CHIP-1777394476","LOGOS_EXPANSION_001.bin","LOGOS_EXPANSION_002","LOGOS_EXPANSION_003","LOGOS_EXPANSION_004","TASK006","TASK007","TASK008"];
function getArtifactManifest(name: string) { try { const files = readdirSync(MANIFESTS_DIR); const match = files.find(f => f.startsWith(name.replace(".bin",""))); if (!match) return null; const d = JSON.parse(readFileSync(join(MANIFESTS_DIR, match), "utf-8")); const chunks = d.receivedChunks || []; return { fileId: d.fileId || name, status: d.status || "unknown", chunks: typeof chunks === "object" ? Object.keys(chunks).length : (typeof chunks === "number" ? chunks : 0), totalChunks: d.totalChunks || null }; } catch { return null; } }
export default async (c: Context) => {
  try {
    const artifacts = CANONICAL_ARTIFACTS.map(name => getArtifactManifest(name)).filter(Boolean) as any[];
    const totalChunks = artifacts.reduce((s, a) => s + a.chunks, 0);
    const complete = artifacts.filter(a => a.status === "complete").length;
    return c.json({ server: "online", timestamp: new Date().toISOString(), summary: { total: artifacts.length, complete, in_progress: artifacts.length - complete, totalChunks }, artifacts, redline: { active: false } });
  } catch (e) { return c.json({ server: "offline", error: String(e) }, 503); }
};
