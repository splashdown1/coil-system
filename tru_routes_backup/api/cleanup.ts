import type { Context } from "hono";
import { readFileSync, writeFileSync, existsSync, readdirSync, unlinkSync, rmdirSync } from "fs";
import { join } from "path";
const MANIFESTS_DIR = "/home/workspace/manifests";
const UPLOADS_DIR = "/home/workspace/uploads";
const ORPHANS = ["COIL_MASTER_CHIP.json","ALPHA-BACKTEST-1777174120","TASK010","TASK010_FIXED","TASK010_TEST","enc-test","tru-optim-report"];
const results = [];
for (const id of ORPHANS) { const manifestPath = join(MANIFESTS_DIR, `${id}.json`); if (existsSync(manifestPath)) { unlinkSync(manifestPath); results.push(`Removed manifest: ${id}`); } const uploadDir = join(UPLOADS_DIR, id); if (existsSync(uploadDir)) { const files = readdirSync(uploadDir); files.forEach(f => unlinkSync(join(uploadDir, f))); rmdirSync(uploadDir); results.push(`Removed upload dir: ${id}`); } }
const bad = join(MANIFESTS_DIR, "LOGOS_EXPANSION_001.bin.json"); const good = join(MANIFESTS_DIR, "LOGOS_EXPANSION_001.json");
if (existsSync(bad) && !existsSync(good)) { const data = readFileSync(bad, "utf8"); const parsed = JSON.parse(data); parsed.fileId = "LOGOS_EXPANSION_001"; writeFileSync(good, JSON.stringify(parsed, null, 2)); unlinkSync(bad); results.push("Fixed LOGOS_EXPANSION_001.bin.json -> LOGOS_EXPANSION_001.json"); }
const files = readdirSync(MANIFESTS_DIR).filter(f => f.endsWith(".json"));
const artifacts = []; let totalChunks = 0;
for (const fname of files) { try { const manifest = JSON.parse(readFileSync(join(MANIFESTS_DIR, fname), "utf8")); const chunks = Object.keys(manifest.receivedChunks || {}).length; artifacts.push({ fileId: manifest.fileId || fname.replace(".json",""), status: manifest.status || "unknown", chunks }); totalChunks += chunks; } catch (e) { results.push(`Error reading ${fname}: ${e.message}`); } }
artifacts.sort((a, b) => { if (a.status === "complete" && b.status !== "complete") return -1; if (a.status !== "complete" && b.status === "complete") return 1; return b.chunks - a.chunks; });
export default (c: Context) => c.json({ ok: true, cleaned: results, summary: { total: artifacts.length, totalChunks, artifacts } });
