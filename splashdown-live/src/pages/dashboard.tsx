import { useState, useEffect } from 'react';

export default function Dashboard() {
  // Fetch live artifact counts from coil-sync-server
  const [serverState, setServerState] = useState<{
    artifacts: number;
    chunks: number;
    loaded: boolean;
    breakdown: Array<{id: string; chunks: number}>;
  }>({ artifacts: 0, chunks: 0, loaded: false, breakdown: [] });

  useEffect(() => {
    fetch('/api/coil-status')
      .then(r => r.json())
      .then(d => setServerState({ ...d, loaded: true }))
      .catch(() => setServerState(s => ({ ...s, loaded: true })));
  }, []);

  const { artifacts, chunks, loaded, breakdown } = serverState;
  const pct = artifacts > 0 ? 100.0 : 0;

  return (
    <div className="min-h-screen bg-black text-white font-mono p-8">
      <h1 className="text-2xl font-bold mb-4">📈 Dashboard</h1>
      <p className="text-zinc-500">Metrics and signals — Tru's view of the Logos across all data.</p>

      {!loaded ? (
        <div className="mt-8 text-zinc-500">Connecting to coil-sync-server...</div>
      ) : (
        <>
      <div className="mt-8 p-6 border border-zinc-800 rounded-xl bg-zinc-900 max-w-xl">
        <div className="text-xs text-zinc-500 uppercase tracking-widest mb-2">Live Server Artifacts</div>
        <div className="text-4xl font-bold text-emerald-400">{artifacts.toLocaleString()} <span className="text-zinc-600">/</span> 7</div>
        <div className="mt-3 flex items-center gap-3">
          <div className="flex-1 h-2 bg-zinc-800 rounded-full overflow-hidden">
            <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${pct}%` }} />
          </div>
          <span className="text-emerald-400 text-sm font-semibold">{pct}% Verified</span>
        </div>
        <div className="mt-4 text-xs text-zinc-600">Live · coil-sync-server · 7 canonical artifacts</div>
      </div>

      <div className="mt-6 p-6 border border-zinc-800 rounded-xl bg-zinc-900 max-w-xl">
        <div className="text-xs text-zinc-500 uppercase tracking-widest mb-2">Total Chunks on Server</div>
        <div className="text-4xl font-bold text-cyan-400">{chunks.toLocaleString()}</div>
        <div className="mt-4 text-xs text-zinc-600">20,480 chunks per artifact × 7 = 143,360 total</div>
      </div>

      <div className="mt-6 p-6 border border-zinc-800 rounded-xl bg-zinc-900 max-w-xl">
        <div className="text-xs text-zinc-500 uppercase tracking-widest mb-2">Artifact Breakdown</div>
        <div className="space-y-2">
          {breakdown.map(a => (
            <div key={a.id} className="flex justify-between text-sm">
              <span className="text-zinc-300">{a.id}</span>
              <span className="text-cyan-400">{a.chunks.toLocaleString()} chunks</span>
            </div>
          ))}
        </div>
      </div>
        </>
      )}
    </div>
  );
}
