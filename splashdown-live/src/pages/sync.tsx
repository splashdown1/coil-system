import { useState, useEffect } from "react";
type LogEntry = { ts: string; batch: number; range: string; result: string; rate: string; confirmed: string };
export default function Sync() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [summary, setSummary] = useState({ total: 6713, batches: 336, confirmed: "?" });
  useEffect(() => {
    fetch("/COIL_mirror/SC/TASK005_SYNC_LOG.txt").then(r => r.text()).then(text => {
      const lines = text.split("\n").filter(l => l.includes("BATCH"));
      const parsed: LogEntry[] = lines.map(l => { const m = l.match(/BATCH (\d+)\/336 \| SC (\d+)\-(\d+)/); const r = l.match(/→ (✓|✗)[^\|]*\| ([0-9.]+s) \(([0-9.]+) SC\/s\)/); const c = l.match(/([0-9]+)\/6713 confirmed/); return m && r ? { ts: l.slice(1, 20), batch: parseInt(m[1]), range: `SC ${m[2]}–${m[3]}`, result: r[1] === "✓" ? "OK" : "FAIL", rate: r[3], confirmed: c ? c[1] : "?" } : null; }).filter(Boolean) as LogEntry[];
      setEntries(parsed.slice(-50));
      const last = parsed[parsed.length - 1];
      if (last) setSummary(s => ({ ...s, confirmed: last.confirmed }));
    }).catch(() => {});
  }, []);
  return (
    <div className="min-h-screen bg-black text-white font-mono p-8">
      <h1 className="text-2xl font-bold mb-1">🔄 COIL Sync</h1>
      <p className="text-zinc-500 mb-8">Delta sync engine — verify knowledge integrity against the Logos.</p>
      <div className="grid grid-cols-3 gap-4 mb-8 max-w-2xl">
        <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900"><div className="text-xs text-zinc-500 uppercase">Super-Chunks</div><div className="text-2xl font-bold text-emerald-400">{summary.total.toLocaleString()}</div></div>
        <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900"><div className="text-xs text-zinc-500 uppercase">Batches</div><div className="text-2xl font-bold text-blue-400">{summary.batches}</div></div>
        <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900"><div className="text-xs text-zinc-500 uppercase">Confirmed</div><div className="text-2xl font-bold text-amber-400">{summary.confirmed}</div></div>
      </div>
      <div className="border border-zinc-800 rounded-xl bg-zinc-900 p-4 max-w-2xl">
        <div className="text-xs text-zinc-500 uppercase tracking-widest mb-3">Batch Log (last 50)</div>
        <div className="space-y-1 max-h-96 overflow-y-auto">{entries.length === 0 && <div className="text-zinc-600 text-xs">Loading...</div>}{entries.map((e, i) => (<div key={i} className="flex gap-3 text-xs items-center"><span className="text-zinc-600 w-16">{e.ts}</span><span className="text-zinc-500 w-8">#{e.batch}</span><span className="text-zinc-400 flex-1">{e.range}</span><span className={e.result === "OK" ? "text-emerald-400" : "text-red-400"}>{e.result}</span><span className="text-zinc-600 w-16">{e.rate} SC/s</span><span className="text-zinc-500">{e.confirmed}/6713</span></div>))}</div>
      </div>
    </div>
  );
}
