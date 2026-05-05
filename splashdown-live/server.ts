import { serveStatic } from "hono/bun";
import type { ViteDevServer } from "vite";
import { createServer as createViteServer } from "vite";
import { Hono } from "hono";
import config from "./zosite.json";

// ── API Routes (server-side Hono handlers) ───────────────────────────────────
// tru_ask
import { readFileSync, existsSync } from "fs";
const KB_FILE = "/home/workspace/Tru_Knowledge_Bank.json";
const FACTS_FILE = "/root/.z/tru/memory/verified_facts.json";
const STATE_FILE = "/root/.z/tru/state.json";
const ACTION_LOG = "/root/.z/tru/actions.log";
function loadJSON(path: string) { try { return existsSync(path) ? JSON.parse(readFileSync(path, "utf-8")) : null; } catch { return null; } }

const truAskHandler = async (c: HonoContext) => {
  const query = c.req.query("q") || c.req.query("question");
  const format = c.req.query("format") || "text";
  const body = await c.req.json().catch(() => ({}));
  const q = body.input || query || "";
  const text_q = String(q).toLowerCase();
  const kb = loadJSON(KB_FILE);
  const facts = loadJSON(FACTS_FILE);
  const state = loadJSON(STATE_FILE);
  let recentActions: string[] = [];
  try { const log = readFileSync(ACTION_LOG, "utf-8"); const lines = log.trim().split("\n").filter(Boolean).slice(-20); recentActions = lines.map(l => { try { return JSON.parse(l).action; } catch { return ""; } }).filter(Boolean); } catch {}
  if (format === "json") return c.json({ kb_entries: kb?.entries?.length || 0, verified_facts: facts?.length || 0, state: { version: state?.tru_version || "unknown", server_health: state?.server_health?.ok ? "healthy" : "unknown", tasks: state?.server_health?.tasks || 0, complete: state?.server_health?.complete || 0, chunks: state?.server_health?.total_chunks || 0, anomaly_flags: state?.anomaly_flags?.length || 0, tick: state?.tick || 0, uptime: state?.started_at ? Math.floor(Date.now() / 1000 - new Date(state.started_at).getTime() / 1000) : 0, }, recent_actions: recentActions, entries: kb?.entries || [], });
  if (q === "SAVE_TO_KB" && body.kb_entry) {
    try {
      const kb2 = loadJSON(KB_FILE) || { name: "Tru Knowledge Bank", description: "TRU Long-Term Memory", version: "1.0", last_updated: new Date().toISOString(), entries: [] };
      const newEntry = { id: `KB-${Date.now()}`, timestamp: new Date().toISOString(), fact: body.kb_entry.substring(0, 500), category: "session", verified: false };
      kb2.entries.push(newEntry);
      kb2.last_updated = new Date().toISOString();
      kb2.version = (parseFloat(kb2.version || "1.0") + 0.01).toFixed(2);
      const fs = await import("fs"); fs.writeFileSync(KB_FILE, JSON.stringify(kb2, null, 2));
      return c.json({ ok: true, saved: newEntry.id, entry: newEntry });
    } catch (e) { return c.json({ ok: false, error: String(e) }); }
  }
  if (!q) return c.json({ text: `TRU Knowledge Bank — ${kb?.entries?.length || 0} verified entries\nServer: ${state?.server_health?.ok ? "healthy" : "unknown"}\nTasks: ${state?.server_health?.tasks || 0} total | ${state?.server_health?.complete || 0} complete\nChunks: ${state?.server_health?.total_chunks || 0} on server\nAnomalies: ${state?.anomaly_flags?.length || 0} flagged\nUptime: ${state?.started_at ? Math.floor((Date.now() - new Date(state.started_at).getTime()) / 60000) + "min" : "unknown"}\n\nRecent actions: ${recentActions.slice(-5).join(" → ") || "none"}`, kb_entries: kb?.entries?.length || 0, verified_facts: facts?.length || 0, state: state || null });
  const entries = kb?.entries || [];
  const relevant = entries.filter((e: any) => text_q.includes(e.category) || text_q.includes(e.id?.toLowerCase()) || e.fact.toLowerCase().includes(text_q) || e.category === "resolution");
  if (relevant.length > 0) return c.json({ text: relevant.map((e: any) => `[${e.id}] ${e.fact}`).join("\n"), matches: relevant.length });
  const factList = facts || [];
  const factMatch = factList.filter((f: any) => f.content?.toLowerCase().includes(text_q));
  if (factMatch.length > 0) return c.json({ text: factMatch.map((f: any) => `${f.id}: ${f.content}`).join("\n"), matches: factMatch.length, source: "verified_facts" });
  return c.json({ text: `No matching knowledge found for "${query}". Try: system, pipeline, resolution, workspace, or browse the KB at /api/tru-ask?format=json`, matches: 0 });
};

// status
const statusHandler = async (c: HonoContext) => {
  try {
    const MANIFESTS_DIR = "/home/workspace/manifests";
    const CANONICAL_ARTIFACTS = ["COIL_MASTER_CHIP-1777394476","LOGOS_EXPANSION_001.bin","LOGOS_EXPANSION_002","LOGOS_EXPANSION_003","LOGOS_EXPANSION_004","TASK006","TASK007","TASK008"];
    const fs = await import("fs");
    const files = fs.readdirSync(MANIFESTS_DIR);
    const artifacts = CANONICAL_ARTIFACTS.map(name => {
      try {
        const match = files.find((f: string) => f.startsWith(name.replace(".bin","")));
        if (!match) return null;
        const d = JSON.parse(fs.readFileSync(`${MANIFESTS_DIR}/${match}`, "utf-8"));
        const chunks = d.receivedChunks || [];
        return { fileId: d.fileId || name, status: d.status || "unknown", chunks: typeof chunks === "object" ? Object.keys(chunks).length : (typeof chunks === "number" ? chunks : 0), totalChunks: d.totalChunks || null };
      } catch { return null; }
    }).filter(Boolean) as any[];
    const totalChunks = artifacts.reduce((s: number, a: any) => s + a.chunks, 0);
    const complete = artifacts.filter((a: any) => a.status === "complete").length;
    return c.json({ server: "online", timestamp: new Date().toISOString(), summary: { total: artifacts.length, complete, in_progress: artifacts.length - complete, totalChunks }, artifacts, redline: { active: false } });
  } catch (e) { return c.json({ server: "offline", error: String(e) }, 503); }
};

// zo_ask
const zoAskHandler = async (c: HonoContext) => {
  try {
    const query = c.req.query("q") || c.req.query("question");
    const format = c.req.query("format") || "text";
    const body = await c.req.json().catch(() => ({}));
    const q = body.input || query;
    if (!q) return c.json({ error: "No input provided" }, 400);
    const zoRes = await fetch("https://api.zo.computer/zo/ask", {
      method: "POST",
      headers: { "Authorization": process.env.ZO_CLIENT_IDENTITY_TOKEN || "", "Content-Type": "application/json" },
      body: JSON.stringify({ input: q, model_name: "vercel:minimax/minimax-m2.7", output_format: format === "json" ? { type: "object", properties: { result: { type: "string" } }, required: ["result"] } : undefined })
    });
    const data = await zoRes.json() as any;
    return c.json({ text: data.output || data.result || String(data), source: "zo" });
  } catch (e) { return c.json({ error: String(e) }, 500); }
};

// cleanup
const cleanupHandler = async (c: HonoContext) => {
  try {
    const { execSync } = await import("child_process");
    const result = execSync('find /home/workspace/uploads -name "*.ARCHIVED*" -o -name "*_STALE_*" 2>/dev/null | head -50', { encoding: "utf-8" });
    return c.json({ cleaned: result.trim().split("\n").filter(Boolean), count: result.trim().split("\n").filter(Boolean).length });
  } catch (e) { return c.json({ cleaned: [], error: String(e) }); }
};

// sync_reset
const syncResetHandler = async (c: HonoContext) => {
  try {
    const fs = await import("fs");
    const COIL_MASTER = "/home/workspace/COIL_MASTER_CHIP.json";
    if (fs.existsSync(COIL_MASTER)) {
      const bak = `${COIL_MASTER}.pre-reset-${Date.now()}`;
      fs.copyFileSync(COIL_MASTER, bak);
      return c.json({ ok: true, backup: bak });
    }
    return c.json({ ok: false, error: "COIL_MASTER_CHIP.json not found" }, 404);
  } catch (e) { return c.json({ ok: false, error: String(e) }, 500); }
};

// stocks (stub — replace with live data)
const stocksHandler = async (c: HonoContext) => {
  return c.json({ tickers: ["SPY","QQQ","NVDA","TSLA"], note: "Stocks API not yet wired to live feed" });
};

import type { Context } from "hono";
type HonoContext = Context;

// ── App ───────────────────────────────────────────────────────────────────────
const app = new Hono();

const mode = process.env.NODE_ENV === "production" ? "production" : "development";

// ── API Routes ───────────────────────────────────────────────────────────────
app.get("/api/hello-zo", (c) => c.json({ msg: "Hello from Zo" }));
app.all("/api/tru_ask", (c) => truAskHandler(c));
app.all("/api/status", (c) => statusHandler(c));
app.all("/api/zo_ask", (c) => zoAskHandler(c));
app.all("/api/cleanup", (c) => cleanupHandler(c));
app.all("/api/sync_reset", (c) => syncResetHandler(c));
app.all("/api/stocks", (c) => stocksHandler(c));

if (mode === "production") {
  configureProduction(app);
} else {
  await configureDevelopment(app);
}

const port = process.env.PORT
  ? parseInt(process.env.PORT, 10)
  : mode === "production"
    ? (config.publish?.published_port ?? config.local_port)
    : config.local_port;

export default { fetch: app.fetch, port, idleTimeout: 255 };

// ── Production ────────────────────────────────────────────────────────────────
function configureProduction(app: Hono) {
  app.use("/assets/*", serveStatic({ root: "./dist" }));
  app.get("/favicon.ico", (c) => c.redirect("/favicon.svg", 302));
  app.use(async (c, next) => {
    if (c.req.method !== "GET") return next();
    const path = c.req.path;
    if (path.startsWith("/api/") || path.startsWith("/assets/")) return next();
    const file = Bun.file(`./dist${path}`);
    if (await file.exists()) {
      const stat = await file.stat();
      if (stat && !stat.isDirectory()) return new Response(file);
    }
    return serveStatic({ path: "./dist/index.html" })(c, next);
  });
}

// ── Development ───────────────────────────────────────────────────────────────
async function configureDevelopment(app: Hono): Promise<ViteDevServer> {
  const vite = await createViteServer({
    server: { middlewareMode: true, hmr: false, ws: false },
    appType: "custom",
  });

  app.use("*", async (c, next) => {
    if (c.req.path.startsWith("/api/")) return next();
    if (c.req.path === "/favicon.ico") return c.redirect("/favicon.svg", 302);

    const url = c.req.path;
    try {
      // Serve pre-built index.html for all non-asset routes
      // SPA routing is handled client-side by React Router
      let template = await Bun.file("./index.html").text();
      template = await vite.transformIndexHtml(url, template);
      return c.html(template, {
        headers: { "Cache-Control": "no-store, must-revalidate" },
      });
    } catch (error) {
      vite.ssrFixStacktrace(error as Error);
      console.error(error);
      return c.text("Internal Server Error", 500);
    }
  });

  return vite;
}