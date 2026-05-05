import { useState, useEffect } from "react";
const GENESIS_BLOCK = { filename: "COIL_MASTER_CHIP.json", size: "39,188,344 bytes", sha256: "23bea63b2299066b4b129db79720d503e64c9abe741b05597ddb32d7c4759e46", chunkCount: 134253, superChunkCount: 6713, archived: "2026-05-01", status: "VERIFIED ✅", serverPath: "data/COIL_MASTER_CHIP.json", reconstructedSize: "39,188,344 bytes", reconstructedHash: "23bea63b2299066b4b129db79720d503e64c9abe741b05597ddb32d7c4759e46", match: "BYTE-FOR-BYTE ✅" };
const ARCHIVE_CATALOG = [
  { file: "COIL_MASTER_CHIP.json", desc: "Source manifest — 89 files, 161.5MB workspace", status: "genesis" },
  { file: "COIL_BATCH_UPLOAD_LOG.json", desc: "336 batch upload receipts, per-batch receipts", status: "active" },
  { file: "TASK005_SYNC_LOG.txt", desc: "Raw uploader progress log — 336 batches, 6,713 SCs", status: "active" },
  { file: "MANIFEST.md", desc: "Provenance chain, root-cause analysis, task conclusions", status: "active" },
  { file: "HASH_LOCK_TRIGGERED.log", desc: "Hash mismatch event — 7,575 mismatches, daemon disabled", status: "archived" },
  { file: "generate_super_chunks.py", desc: "SC generation script — 46B + 640B + 5120B format", status: "active" },
  { file: "task005_safe_uploader.py", desc: "Resume-safe batch uploader", status: "active" },
  { file: "COIL_MASTER_CHIP-1777394476/", desc: "Orphaned run — 23,618 chunks, wrong fileId", status: "archived" },
  { file: "FAILED_RUNS.tar.gz", desc: "Full failed run snapshot — evidence for archaeology", status: "archived" },
  { file: "final_clean.json", desc: "Pre-sync workspace state snapshot — 89 files, 134,253 chunks", status: "active" },
  { file: "BATCH_LOG_336_batches_BACKUP.json", desc: "Pre-run backup of batch receipts", status: "archived" },
  { file: "COIL_MASTER_CHIP-1777394476.json", desc: "Server-side manifest from failed run (complete set)", status: "archived" },
  { file: "mirror-extract/", desc: "Extracted zip archives from mirror daemon", status: "active" },
];
const STATUS_COLORS = { genesis: "bg-cyan-900 text-cyan-300 border-cyan-700", active: "bg-green-900 text-green-300 border-green-700", archived: "bg-zinc-800 text-zinc-400 border-zinc-700" };
const STATUS_LABELS = { genesis: "GENESIS", active: "ACTIVE", archived: "ARCHIVED" };
export default function Archive() {
  const [filter, setFilter] = useState<"all"|"genesis"|"active"|"archived">("all");
  const [copied, setCopied] = useState<string | null>(null);
  const filtered = filter === "all" ? ARCHIVE_CATALOG : ARCHIVE_CATALOG.filter(f => f.status === filter);
  const copyHash = (hash: string) => { navigator.clipboard.writeText(hash); setCopied(hash); setTimeout(() => setCopied(null), 1500); };
  return (
    <div className="min-h-screen bg-black text-white font-mono">
      <div className="max-w-5xl mx-auto p-8">
        <div className="flex items-center gap-3 mb-8"><span className="text-3xl">📚</span><div><h1 className="text-3xl font-bold tracking-tight">Knowledge Archive</h1><p className="text-zinc-500 text-sm mt-1">Ledger of Truth — COIL_UNBOUND cold storage.</p></div></div>
        <div className="bg-cyan-950 border border-cyan-700 rounded-lg p-6 mb-8">
          <div className="flex items-center gap-2 mb-4"><span className="text-cyan-400 font-bold text-xs tracking-widest">⬡ GENESIS BLOCK</span><span className="text-xs bg-cyan-900 text-cyan-300 px-2 py-0.5 rounded">ANCHOR</span></div>
          <div className="grid md:grid-cols-2 gap-4 mb-4">
            <div><p className="text-xs text-zinc-500 mb-1">Source file</p><p className="text-white font-bold">{GENESIS_BLOCK.filename}</p><p className="text-cyan-400 text-sm">{GENESIS_BLOCK.size}</p></div>
            <div><p className="text-xs text-zinc-500 mb-1">SHA256</p><div className="flex items-center gap-2"><p className="font-mono text-xs text-zinc-400 break-all">{GENESIS_BLOCK.sha256}</p><button onClick={()=>copyHash(GENESIS_BLOCK.sha256)} className="shrink-0 text-xs bg-cyan-800 hover:bg-cyan-700 text-cyan-300 px-2 py-1 rounded transition-colors">{copied===GENESIS_BLOCK.sha256?"COPIED":"COPY"}</button></div></div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">{[["Chunks","134,253 × 256B"],["Super-chunks","6,713"],["Workspace total","89 files · 161.5MB"],["Status","VERIFIED ✅"]].map(([k,v])=>(<div key={k} className="bg-black/40 border border-cyan-800 rounded p-3 text-center"><div className="text-xs text-zinc-500 mb-1">{k}</div><div className="text-sm font-bold text-white">{v}</div></div>))}</div>
          <div className="border-t border-cyan-800 pt-4 mt-4"><p className="text-xs text-zinc-500 mb-2">Server reconstruction</p><div className="grid md:grid-cols-3 gap-3">{[["Path: ","data/COIL_MASTER_CHIP.json"],["Size: ",GENESIS_BLOCK.reconstructedSize],["Match: ","BYTE-FOR-BYTE ✅"]].map(([k,v])=>(<div key={k} className="bg-black/30 border border-cyan-800 rounded p-2"><span className="text-xs text-zinc-500">{k}</span><span className="text-xs text-white">{v}</span></div>))}</div></div>
        </div>
        <div className="flex gap-2 mb-6">{["all","genesis","active","archived"].map(f=>(<button key={f} onClick={()=>setFilter(f as typeof filter)} className={`px-3 py-1.5 text-xs rounded border transition-colors ${filter===f?"bg-white text-black border-white":"border-zinc-700 text-zinc-500 hover:text-white"}`}>{f.toUpperCase()} {f!=="all"?`(${ARCHIVE_CATALOG.filter(x=>x.status===f).length})`:`(${ARCHIVE_CATALOG.length})`}</button>))}</div>
        <div className="space-y-2">{filtered.map((item,i)=>(<div key={i} className={`border rounded p-4 flex items-start gap-4 ${STATUS_COLORS[item.status as keyof typeof STATUS_COLORS]}`}><div className="flex-1 min-w-0"><div className="flex items-center gap-2 mb-1"><span className="font-mono text-sm font-bold text-white truncate">{item.file}</span><span className={`shrink-0 text-xs px-1.5 py-0.5 rounded border ${STATUS_COLORS[item.status as keyof typeof STATUS_COLORS]}`}>{STATUS_LABELS[item.status as keyof typeof STATUS_LABELS]}</span></div><p className="text-xs text-zinc-400">{item.desc}</p></div></div>))}</div>
        <div className="mt-8 text-xs text-zinc-600 border-t border-zinc-800 pt-6">Archive root: <span className="font-mono">/home/workspace/COIL_archive/</span> · last updated 2026-05-01</div>
      </div>
    </div>
  );
}
