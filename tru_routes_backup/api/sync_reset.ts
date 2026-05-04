import type { Context } from "hono";
import { readFileSync, existsSync, readdirSync, unlinkSync } from "fs";
import { join } from "path";
const MANIFESTS_DIR = "/home/workspace/manifests";
const ORPHANS = ["ALPHA-BACKTEST-1777174120","TASK010","TASK010_FIXED","TASK010_TEST","enc-test","tru-optim-report","COIL_MASTER_CHIP"];
export default async (c: Context) => {
  try {
    const log: string[] = [];
    if (existsSync(MANIFESTS_DIR)) {
      const files = readdirSync(MANIFESTS_DIR).filter(f => f.endsWith(".json"));
      for (const file of files) {
        const fileId = file.replace(/\.json$/, "");
        if (ORPHANS.some(o => fileId.includes(o))) {
          const path = join(MANIFESTS_DIR, file);
          const raw = readFileSync(path, "utf-8");
          try { const d = JSON.parse(raw); if (d.status === "in_progress" || d.receivedChunks?.length <= 4) { unlinkSync(path); log.push(`Removed orphan manifest: ${file}`); } } catch {} }
        }
      }
    }
    let serverOk = false;
    try { const res = await fetch("http://localhost:3000/health", { signal: AbortSignal.timeout(5000) }); serverOk = res.ok; if (serverOk) log.push("Server health: OK"); else log.push(`Server health: FAILED (${res.status})`); } catch (e: any) { log.push("Server unreachable: " + e.message); }
    let taskSummary = null;
    try { const res = await fetch("http://localhost:3000/tasks", { signal: AbortSignal.timeout(5000) }); if (res.ok) { const d = await res.json(); taskSummary = d.summary; log.push(`Server tasks: ${d.summary.total} total | ${d.summary.complete} complete | ${d.summary.in_progress} in_progress`); } } catch (e: any) { log.push("Server /tasks error: " + e.message); }
    return c.json({ ok: true, reset_at: new Date().toISOString(), log, server_healthy: serverOk, task_summary: taskSummary });
  } catch (e: any) { return c.json({ ok: false, error: e.message }, 500); }
};
