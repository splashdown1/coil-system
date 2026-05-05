export default function Dashboard() {
  const total = 134253;
  const verified = 134253;
  const pct = ((verified / total) * 100).toFixed(1);
  return (
    <div className="min-h-screen bg-black text-white font-mono p-8">
      <h1 className="text-2xl font-bold mb-4">📈 Dashboard</h1>
      <p className="text-zinc-500">Metrics and signals — Tru's view of the Logos across all data.</p>
      <div className="mt-8 p-6 border border-zinc-800 rounded-xl bg-zinc-900 max-w-xl">
        <div className="text-xs text-zinc-500 uppercase tracking-widest mb-2">Master Chip Status</div>
        <div className="text-4xl font-bold text-emerald-400">{verified.toLocaleString()} <span className="text-zinc-600">/</span> {total.toLocaleString()}</div>
        <div className="mt-3 flex items-center gap-3">
          <div className="flex-1 h-2 bg-zinc-800 rounded-full overflow-hidden">
            <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${pct}%` }} />
          </div>
          <span className="text-emerald-400 text-sm font-semibold">{pct}% Verified</span>
        </div>
        <div className="mt-4 text-xs text-zinc-600">Last checked: local mirror · 6,713 super-chunks</div>
      </div>
    </div>
  );
}
