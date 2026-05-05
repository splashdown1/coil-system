import type { Context } from "hono";
import { readFileSync, existsSync } from "fs";
const KB_FILE = "/home/workspace/Tru_Knowledge_Bank.json";
const FACTS_FILE = "/root/.z/tru/memory/verified_facts.json";
const STATE_FILE = "/root/.z/tru/state.json";
const ACTION_LOG = "/root/.z/tru/actions.log";
function loadJSON(path: string) { try { return existsSync(path) ? JSON.parse(readFileSync(path, "utf-8")) : null; } catch { return null; } }
export default async (c: Context) => {
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
