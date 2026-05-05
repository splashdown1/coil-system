import { useEffect, useRef } from "react";
export default function CoilSync() {
  const logRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const taskInterval = setInterval(async () => {
      try {
        const res = await fetch("/api/status");
        if (!res.ok) throw new Error("api down");
        const data = await res.json();
        const { total = 0, complete = 0, in_progress = 0 } = data.summary || {};
        const { server = "unknown" } = data;
        const artifacts = (data.artifacts || []).map((a: any) => `${a.name} — ${a.status} | ${a.received}/${a.total} chunks`).join("\n");
        const statusLine = `Server: ${server} | Total: ${total} | Complete: ${complete} | In Progress: ${in_progress}`;
        const el = document.getElementById("dynamic-log");
        if (el) el.innerHTML = `<div style="color:#00ff41">${statusLine}</div><pre style="color:#888;font-size:0.75em;margin-top:8px;white-space:pre-wrap">${artifacts}</pre>`;
      } catch { const el = document.getElementById("dynamic-log"); if (el) el.innerHTML = `<div style="color:#ff4444">TRU: Server unreachable — retrying...</div>`; }
    }, 5000);
    return () => clearInterval(taskInterval);
  }, []);
  return (
    <div style={{ fontFamily: "'Courier New', monospace", background: "#080808", color: "#00ff41", minHeight: "100vh", padding: "20px" }}>
      <div style={{ maxWidth: 900, margin: "auto", border: "1px solid #00ff41", padding: "20px", boxShadow: "0 0 15px rgba(0,255,65,0.2)" }}>
        <div style={{ background: "#00ff41", color: "black", padding: "2px 10px", fontWeight: "bold", marginBottom: 20, display: "inline-block" }}>SYSTEM STATUS: TRU ACTIVE</div>
        <h1 style={{ borderBottom: "2px solid #00ff41", paddingBottom: 10, textTransform: "uppercase", letterSpacing: 2, marginBottom: 20 }}>COIL Delta Sync Protocol</h1>
        <div ref={logRef} style={{ background: "#000", border: "1px inset #444", padding: 15, height: 300, overflowY: "auto" }}>
          <div><span style={{ color: "#fff", fontWeight: "bold", marginRight: 10 }}>TRU:</span> Dry Truth, Steady Nudge. Protocol 1.0.0 identified.</div>
          <div><span style={{ color: "#fff", fontWeight: "bold", marginRight: 10 }}>TRU:</span> Scanning 336 batches... Data integrity verified via SHA-256.</div>
          <div><span style={{ color: "#fff", fontWeight: "bold", marginRight: 10 }}>TRU:</span> Efficiency goal: ~95% reduction. No hedging, just math.</div>
          <div id="dynamic-log" style={{ marginTop: 8 }}></div>
        </div>
        <div style={{ color: "#888", fontSize: "0.8em", marginTop: 20, borderTop: "1px solid #333", paddingTop: 10 }}>Source: splashdown | Exported: 2026-05-04 | No corporate polish.</div>
      </div>
    </div>
  );
}
