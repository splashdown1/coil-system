import { useState } from "react";
const WATCHLIST = ["NVDA","MSFT","AAPL","GOOG","AMZN","META","TSLA","BRK.B","JPM","V","UNH","HD","MA","AV","COST","ABBV","MRK","LLY","WMT","KO","PEP","TMO","CSCO","ACN","ABT","DHR","ADBE","NKE","CRM","TXN","PM","NEE","UPS","MS","RTX","LOW","HON","INTU","IBM","ELV","CAT","MDT","SPGI","GS","BLK","AXP","BKNG","SYK","AMGN","QCOM","REGN","VRTX","ADI","MMC","TJX","ISRG","C","LRCX","ZTS","ADP"];
const SECTORS: Record<string, string[]> = { "Tech": ["NVDA","MSFT","AAPL","GOOG","META","AV","ADBE","CRM","TXN","LRCX","ADI","QCOM","INTU","IBM"], "Finance": ["JPM","GS","BLK","MS","AXP","C","BKNG","ADP"], "Health": ["UNH","ABBV","MRK","LLY","ABT","AMGN","REGN","VRTX","ZTS","SYK","ISRG","MDT"], "Consumer": ["WMT","COST","HD","NKE","KO","PEP","PM","TJX","MRK"], "Industrials & Energy": ["CAT","HON","UPS","RTX","NEE","EXC","CCL"] };
type Quote = { c: string; v: number; o: string; h: string; l: string; pc: string; t: number };
export default function Stocks() {
  const [symbol, setSymbol] = useState("NVDA");
  const [data, setData] = useState<Quote | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [priceChange, setPriceChange] = useState<number>(0);
  const fetchQuote = async (sym: string) => { setLoading(true); setError(""); try { const r = await fetch(`/api/stocks?symbol=${sym}`); const j = await r.json(); if (j.error) throw new Error(j.error); setData(j); setSymbol(sym); const prevClose = parseFloat(j.pc); const curr = parseFloat(j.c); setPriceChange(((curr - prevClose) / prevClose) * 100); } catch (e: any) { setError(e.message); } finally { setLoading(false); } };
  const gain = data ? parseFloat(data.c) > parseFloat(data.pc) : true;
  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0f", color: "#e0e0e0", fontFamily: "monospace", padding: "2rem" }}>
      <div style={{ marginBottom: "1.5rem", borderBottom: "1px solid #222", paddingBottom: "1rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#00ff88" }}>SPECULATIVE WATCH</h1>
          <a href="/" style={{ color: "#888", textDecoration: "none" }}>← Tru</a>
        </div>
        <div style={{ fontSize: "0.75rem", color: "#666" }}>52-asset scanner · live data</div>
      </div>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem" }}>
        <input value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} onKeyDown={e => e.key === "Enter" && fetchQuote(symbol)} style={{ flex: 1, background: "#111", border: "1px solid #333", color: "#fff", padding: "0.5rem", fontFamily: "monospace", fontSize: "1rem" }} placeholder="Symbol (e.g. NVDA)"/>
        <button onClick={() => fetchQuote(symbol)} style={{ background: "#00ff88", color: "#000", padding: "0.5rem 1rem", fontWeight: 700, cursor: "pointer" }}>SCAN</button>
      </div>
      {loading && <div style={{ color: "#666" }}>Scanning...</div>}
      {error && <div style={{ color: "#ff4444" }}>Error: {error}</div>}
      {data && (
        <div style={{ background: "#111", border: `1px solid ${gain ? "#00ff88" : "#ff4444"}`, padding: "1rem", marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div><span style={{ fontSize: "2rem", fontWeight: 700, color: "#fff" }}>{symbol}</span><span style={{ marginLeft: "1rem", fontSize: "1rem", color: "#888" }}>{data.o && !data.o.includes("Error") ? `O: $${data.o}` : "O: —"}</span></div>
            <div style={{ textAlign: "right" }}><div style={{ fontSize: "1.5rem", fontWeight: 700, color: gain ? "#00ff88" : "#ff4444" }}>${data.c}</div><div style={{ color: gain ? "#00ff88" : "#ff4444", fontSize: "0.9rem" }}>{gain ? "▲" : "▼"} {Math.abs(priceChange).toFixed(2)}%</div></div>
          </div>
          <div style={{ display: "flex", gap: "2rem", marginTop: "0.5rem", fontSize: "0.75rem", color: "#666" }}><span>H: ${data.h || "—"}</span><span>L: ${data.l || "—"}</span><span>Prev: ${data.pc || "—"}</span></div>
        </div>
      )}
      {Object.entries(SECTORS).map(([sector, syms]) => (<div key={sector} style={{ marginBottom: "1.5rem" }}><div style={{ fontSize: "0.7rem", color: "#666", marginBottom: "0.5rem", textTransform: "uppercase" }}>{sector}</div><div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(80px, 1fr))", gap: "0.25rem" }}>{syms.map(sym => (<button key={sym} onClick={() => fetchQuote(sym)} style={{ background: "#111", border: `1px solid ${sym === symbol ? "#00ff88" : "#222"}`, color: sym === symbol ? "#00ff88" : "#aaa", padding: "0.35rem", fontSize: "0.7rem", cursor: "pointer", textTransform: "uppercase" }}>{sym}</button>))}</div></div>))}
      <details style={{ marginTop: "1rem" }}><summary style={{ cursor: "pointer", color: "#666", fontSize: "0.75rem" }}>FULL 52-ASSET WATCHLIST</summary><div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem", marginTop: "0.5rem" }}>{WATCHLIST.map(sym => (<button key={sym} onClick={() => fetchQuote(sym)} style={{ background: "#111", border: `1px solid ${sym === symbol ? "#00ff88" : "#222"}`, color: sym === symbol ? "#00ff88" : "#555", padding: "0.25rem 0.5rem", fontSize: "0.65rem", cursor: "pointer" }}>{sym}</button>))}</div></details>
    </div>
  );
}
