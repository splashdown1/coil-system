import { useState, useEffect } from "react";

const MILESTONES = [
  { id: 1,  ts: "2026-04-28T17:10:57Z", event: "COIL_UNBOUND initialized",                     detail: "89 files indexed. 161,584,949 bytes total.", actor: "system", severity: "info" },
  { id: 2,  ts: "2026-04-28T18:15:42Z", event: "Super-Chunk Generation — Round 1",             detail: "9,377 chip.sc.*.bin files generated. 187,529 chunks (256B).", actor: "agent", severity: "info" },
  { id: 3,  ts: "2026-04-28T18:25:00Z", event: "Upload Batch 0–121 confirmed",                 detail: "2,440 super-chunks streamed. curl 1.5s delay pattern holding.", actor: "agent", severity: "info" },
  { id: 4,  ts: "2026-04-28T19:29:00Z", event: "Upload crashed — gap detected",                detail: "Process died at batch 121. Gap: SC 3240–9376 unconfirmed.", actor: "system", severity: "warning" },
  { id: 5,  ts: "2026-04-28T19:30:00Z", event: "Resume from batch 122",                         detail: "Task 005 restarted. Batch log preserved.", actor: "agent", severity: "info" },
  { id: 6,  ts: "2026-04-28T19:43:57Z", event: "Ghost chunks detected — data hybrid",           detail: "Server assembled old ghost chunks 6713–9376. Wrong hash on /complete.", actor: "agent", severity: "error" },
  { id: 7,  ts: "2026-04-28T20:28:00Z", event: "Root cause: daemon writing to canonical",      detail: "coil_mirror_daemon modifying COIL_MASTER_CHIP.json between sessions.", actor: "agent", severity: "critical" },
  { id: 8,  ts: "2026-04-28T21:15:00Z", event: "Daemon frozen + canonical locked",             detail: "supervisord autostart=false. File chmod 444. SHA cf79e05d stable.", actor: "agent", severity: "info" },
  { id: 9,  ts: "2026-04-28T21:16:00Z", event: "Hard reset: new canonical established",        detail: "34,368,945 bytes. SHA 288886c9. 6,713 super-chunks. sync_status=mirrored.", actor: "agent", severity: "info" },
  { id: 10, ts: "2026-04-29T00:26:00Z", event: "Safe-mode upload complete",                    detail: "All 6,713 SCs streamed. Ghost chunks deleted. Server: 6,713/6,713.", actor: "agent", severity: "info" },
  { id: 11, ts: "2026-04-29T03:00:00Z", event: "TRU_INTELLIGENCE space deployed",              detail: "splashdown.zo.space rebuilt. 120s timeout. API bridge active.", actor: "agent", severity: "info" },
  { id: 12, ts: "2026-04-29T03:15:00Z", event: "project_history.json + Timeline initialized",   detail: "12 milestones logged. Tru has persistent project memory.", actor: "tru", severity: "info" },
];

const SEVERITY_COLORS = {
  info:    { dot: "#4ade80", line: "rgba(74,222,128,0.3)",  text: "#4ade80" },
  warning: { dot: "#fbbf24", line: "rgba(251,191,36,0.3)",  text: "#fbbf24" },
  error:   { dot: "#f87171", line: "rgba(248,113,113,0.3)", text: "#f87171" },
  critical: { dot: "#c084fc", line: "rgba(192,132,252,0.3)", text: "#c084fc" },
};

function fmt(ts: string) {
  return new Date(ts).toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false, timeZoneName: "short"
  });
}

export default function Timeline() {
  const [filter, setFilter] = useState<string>("all");
  const filtered = filter === "all" ? MILESTONES : MILESTONES.filter(m => m.severity === filter);
  return (
    <div style={{ minHeight: "100vh", background: "#080810", color: "#e0e7ff", fontFamily: "ui-monospace, monospace" }}>
      <div style={{ padding: "20px 24px", borderBottom: "1px solid rgba(99,130,255,0.2)", background: "rgba(0,0,0,0.4)" }}>
        <div style={{ maxWidth: 720, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: "0.12em", color: "#a5b4fc" }}>TRU_INTELLIGENCE · PROJECT TIMELINE</div>
            <div style={{ fontSize: 11, color: "#6366f1", marginTop: 4 }}>COIL_UNBOUND · 12 MILESTONES · LAST UPDATED 2026-04-29</div>
          </div>
          <a href="/" style={{ padding: "8px 16px", border: "1px solid rgba(99,130,255,0.4)", borderRadius: 8, color: "#a5b4fc", textDecoration: "none", fontSize: 12, letterSpacing: "0.08em" }}>← BACK TO TRU</a>
        </div>
      </div>
      <div style={{ padding: "16px 24px", display: "flex", gap: 8, justifyContent: "center", flexWrap: "wrap" }}>
        {["all","info","warning","error","critical"].map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding: "6px 14px", borderRadius: 6, border: "1px solid " + (filter===f ? "rgba(165,180,252,0.8)" : "rgba(99,130,255,0.3)"),
            background: filter===f ? "rgba(99,130,255,0.2)" : "transparent",
            color: filter===f ? "#a5b4fc" : "#6366f1", fontSize: 11, cursor: "pointer", fontFamily: "ui-monospace, monospace", letterSpacing: "0.06em", textTransform: "uppercase"
          }}>{f}</button>
        ))}
      </div>
      <div style={{ maxWidth: 720, margin: "0 auto", padding: "0 24px 40px", position: "relative" }}>
        <div style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: 1, background: "rgba(99,130,255,0.15)", transform: "translateX(-50%)" }} />
        {filtered.map((m, i) => {
          const c = SEVERITY_COLORS[m.severity as keyof typeof SEVERITY_COLORS] || SEVERITY_COLORS.info;
          return (
            <div key={m.id} style={{ display: "flex", gap: 24, marginBottom: i === filtered.length - 1 ? 0 : 32, position: "relative" }}>
              <div style={{ flex: 1, textAlign: "right", paddingTop: 4 }}>
                <div style={{ fontSize: 11, color: "#4b5563" }}>{fmt(m.ts)}</div>
                <div style={{ fontSize: 12, color: "#6b7280", marginTop: 2, fontStyle: "italic" }}>{m.actor}</div>
              </div>
              <div style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center", zIndex: 1 }}>
                <div style={{ width: 14, height: 14, borderRadius: "50%", background: c.dot, boxShadow: `0 0 10px ${c.dot}80`, flexShrink: 0, marginTop: 4 }} />
                {i < filtered.length - 1 && <div style={{ width: 1, flex: 1, background: c.line, minHeight: 40 }} />}
              </div>
              <div style={{ flex: 2, paddingTop: 2 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: c.text, marginBottom: 4 }}>{m.event}</div>
                <div style={{ fontSize: 12, color: "#9ca3af", lineHeight: 1.6 }}>{m.detail}</div>
                <div style={{ display: "inline-block", marginTop: 6, padding: "2px 8px", borderRadius: 4, border: `1px solid ${c.dot}40`, background: `${c.dot}10`, fontSize: 10, color: c.dot, letterSpacing: "0.08em", textTransform: "uppercase" }}>{m.severity}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
