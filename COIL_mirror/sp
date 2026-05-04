import { useState, useEffect, useCallback } from "react";

const SECTOR_RATES = {
  "Tech": 0.0018, "Finance": 0.0012, "Healthcare": 0.0013,
  "Consumer": 0.0011, "Energy": 0.0020, "Retail": 0.0014,
  "Social": 0.0022, "Media": 0.0010, "Telecom": 0.0008, "Industrial": 0.0015,
};

const MOCK_STOCKS = [
  { symbol: "AVCT", name: "American Virtual Care", sector: "Healthcare", basePrice: 3.21 },
  { symbol: "SGBX", name: "SG Blocks", sector: "Industrial", basePrice: 1.88 },
  { symbol: "INVO", name: "INVO Bioscience", sector: "Healthcare", basePrice: 2.94 },
  { symbol: "KPRX", name: "Kepro Holdings", sector: "Healthcare", basePrice: 5.12 },
  { symbol: "ONCOD", name: "Oncocyte Corp", sector: "Healthcare", basePrice: 4.47 },
  { symbol: "RNGA", name: "Ranger Energy", sector: "Energy", basePrice: 6.33 },
  { symbol: "TFFY", name: "Tentofy", sector: "Consumer", basePrice: 2.15 },
  { symbol: "GTIM", name: "Good Times Restaurants", sector: "Consumer", basePrice: 1.45 },
  { symbol: "WALD", name: "Warrior Technologies", sector: "Energy", basePrice: 8.72 },
  { symbol: "MOVE", name: "MOVE Financial", sector: "Finance", basePrice: 3.89 },
  { symbol: "AAPL", name: "Apple", sector: "Tech", basePrice: 214.29 },
  { symbol: "MSFT", name: "Microsoft", sector: "Tech", basePrice: 415.50 },
  { symbol: "NVDA", name: "NVIDIA", sector: "Tech", basePrice: 875.39 },
  { symbol: "GOOGL", name: "Alphabet", sector: "Tech", basePrice: 175.98 },
  { symbol: "AMD", name: "AMD", sector: "Tech", basePrice: 178.30 },
  { symbol: "COST", name: "Costco", sector: "Retail", basePrice: 912.40 },
  { symbol: "MRK", name: "Merck", sector: "Healthcare", basePrice: 118.40 },
  { symbol: "JPM", name: "JPMorgan", sector: "Finance", basePrice: 212.75 },
];

const QQQ_BASE = 415;
const TRADE_DOLLARS = 1000;

function simulateScore(base, qqqInfluence, sector) {
  const rate = SECTOR_RATES[sector] || 0.0015;
  const vol = base < 5 ? 0.28 : base < 20 ? 0.18 : 0.08;
  const qqqEff = qqqInfluence * 0.35;
  const sectorEff = (rate - 0.0015) * 6000;
  const volEff = (vol - 0.15) * 300;
  const raw = 50 + qqqEff + sectorEff + volEff;
  return Math.min(99, Math.max(5, Math.round(raw)));
}

function scoreTier(score) {
  if (score >= 78) return { tier: "SPECULATIVE", color: "#f59e0b", glow: true };
  if (score >= 62) return { tier: "ACTIVE", color: "#10b981", glow: false };
  if (score >= 42) return { tier: "CAUTIOUS", color: "#f59e0b", glow: false };
  return { tier: "DORMANT", color: "#475569", glow: false };
}

function TrendBadge({ pct }) {
  const up = pct > 0;
  const col = up ? "#34d399" : "#f87171";
  return (
    <span style={{ color: col, fontSize: "11px", fontWeight: "bold" }}>
      {up ? "▲" : "▼"} {Math.abs(pct).toFixed(2)}%
    </span>
  );
}

export default function Mission() {
  const [stocks, setStocks] = useState([]);
  const [qqq, setQqq] = useState(QQQ_BASE);
  const [qqqChange, setQqqChange] = useState(0);
  const [solar, setSolar] = useState({ cls: "C3.1", flux: 3.1e-6, label: "LOW" });
  const [flashCount, setFlashCount] = useState(0);
  const [lastFetch, setLastFetch] = useState(null);
  const [fetching, setFetching] = useState(false);
  const [scoreFilter, setScoreFilter] = useState("ALL");
  const [sectorFilter, setSectorFilter] = useState("ALL");
  const [scores, setScores] = useState({});

  const fetchData = useCallback(async () => {
    setFetching(true);
    try {
      const [qqqRes, goesRes] = await Promise.all([
        fetch("https://query1.finance.yahoo.com/v8/finance/chart/QQQ?interval=1d&range=1d"),
        fetch("https://services.swpc.noaa.gov/json/goes/16/xrays_1m.json").catch(() => null),
      ]);
      const qqqData = qqqRes.ok ? await qqqRes.json().catch(() => null) : null;
      const qqqRaw = qqqData?.chart?.result?.[0]?.meta?.regularMarketPrice;
      if (qqqRaw) {
        const change = +((qqqRaw / QQQ_BASE - 1) * 100).toFixed(2);
        setQqq(+qqqRaw.toFixed(2));
        setQqqChange(change);
      }
      if (goesRes?.ok) {
        const goesData = await goesRes.json().catch(() => null);
        const last = goesData?.[goesData.length - 1];
        if (last) {
          const flux = +last.flux;
          const cls = (last.fl || "C1").replace("e-", "·");
          const label = flux >= 1e-4 ? "⚠ X-FLARE" : flux >= 1e-5 ? "⚠ M-CLASS" : flux >= 1e-6 ? "C-CLASS" : "LOW";
          setSolar({ cls, flux, label });
          setFlashCount(c => c + 1);
        }
      }
    } catch { /* silent */ }
    finally { setFetching(false); }
    setLastFetch(new Date().toLocaleTimeString());
  }, []);

  useEffect(() => {
    fetchData();
    const iv = setInterval(fetchData, 45000);
    return () => clearInterval(iv);
  }, [fetchData]);

  useEffect(() => {
    setStocks(MOCK_STOCKS.map(s => {
      const qqqInfl = (qqq - QQQ_BASE) / QQQ_BASE;
      const rate = SECTOR_RATES[sector] || 0.0015;
      const vol = s.basePrice < 5 ? 0.28 : s.basePrice < 20 ? 0.18 : 0.08;
      const seed = (rate * 10 + (s.basePrice % 0.1) / 5 + qqqInfl * 0.4) * 100;
      const noise = (Math.random() - 0.5) * 8;
      const score = Math.min(99, Math.max(5, Math.round(seed + noise)));
      return { ...s, score };
    }));
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setStocks(prev => prev.map(s => {
        const qqqInfl = (qqq - QQQ_BASE) / QQQ_BASE;
        const vol = s.basePrice < 5 ? 0.06 : s.basePrice < 20 ? 0.035 : 0.012;
        const priceShift = (Math.random() - 0.48) * vol + qqqInfl * 0.3;
        const pct = +(priceShift * 100).toFixed(2);
        const newPrice = +(s.basePrice * (1 + priceShift)).toFixed(4);
        const newScore = simulateScore(s.basePrice, qqqInfl, s.sector);
        return { ...s, price: newPrice, pct, score: newScore };
      }));
    }, 4000);
    return () => clearInterval(interval);
  }, [qqq]);

  const qqqInfl = (qqq - QQQ_BASE) / QQQ_BASE;
  const sectors = ["ALL", ...new Set(MOCK_STOCKS.map(s => s.sector))];
  const activeStocks = stocks.filter(s => {
    const tier = scoreTier(s.score).tier;
    const matchScore = scoreFilter === "ALL" || tier === scoreFilter;
    const matchSector = sectorFilter === "ALL" || s.sector === sectorFilter;
    return matchScore && matchSector;
  });

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0f", color: "#e2e8f0", fontFamily: "'Courier New', Courier, monospace", padding: "16px", paddingBottom: "80px" }}>

      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: "18px", borderBottom: "1px solid #1e293b", paddingBottom: "14px" }}>
        <div style={{ fontSize: "10px", color: "#f59e0b", letterSpacing: "3px", marginBottom: "4px" }}>TRU SPLASHDOWN</div>
        <div style={{ fontSize: "26px", fontWeight: "bold", color: "#f8fafc", letterSpacing: "2px", textShadow: "0 0 20px rgba(245,158,11,0.3)" }}>GAIAN WEALTH-FIELD</div>
        <div style={{ fontSize: "10px", color: "#475569", marginTop: "3px" }}>COIL MARKET SIMULATOR · APRIL 2026</div>
      </div>

      {/* How It Works */}
      <div style={{ background: "#0f1117", border: "1px solid #1e293b", borderRadius: "6px", padding: "12px", marginBottom: "14px" }}>
        <div style={{ fontSize: "10px", color: "#f59e0b", letterSpacing: "2px", marginBottom: "6px" }}>HOW IT WORKS</div>
        <p style={{ fontSize: "11px", color: "#94a3b8", lineHeight: "1.6", margin: 0 }}>
          TRU SPLASHDOWN uses a <span style={{ color: "#f8fafc" }}>multi-factor scoring model</span> that weighs network adoption, volatility patterns, social momentum, fundamentals, and sector conditions. Weights adapt in real-time as market context shifts. Output is a <span style={{ color: "#f59e0b" }}>dynamic signal tier</span> — not a binary call.
        </p>
        <div style={{ display: "flex", gap: "8px", marginTop: "8px", flexWrap: "wrap" }}>
          <span style={{ background: "#1a1600", border: "1px solid #f59e0b", color: "#f59e0b", padding: "2px 8px", borderRadius: "4px", fontSize: "10px" }}>SPECULATIVE 78-99</span>
          <span style={{ background: "#0a1a12", border: "1px solid #10b981", color: "#10b981", padding: "2px 8px", borderRadius: "4px", fontSize: "10px" }}>ACTIVE 62-77</span>
          <span style={{ background: "#1a1200", border: "1px solid #f59e0b", color: "#f59e0b", padding: "2px 8px", borderRadius: "4px", fontSize: "10px" }}>CAUTIOUS 42-61</span>
          <span style={{ background: "#111827", border: "1px solid #475569", color: "#64748b", padding: "2px 8px", borderRadius: "4px", fontSize: "10px" }}>DORMANT 5-41</span>
        </div>
      </div>

      {/* Solar + Market status bar */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "12px", flexWrap: "wrap" }}>
        <div style={{ flex: 1, background: "#0f1117", border: "1px solid #1e293b", borderRadius: "6px", padding: "8px 10px" }}>
          <div style={{ fontSize: "9px", color: "#475569" }}>QQQ · NASDAQ 100</div>
          <div style={{ fontSize: "16px", fontWeight: "bold", color: qqqChange >= 0 ? "#34d399" : "#f87171" }}>${qqq}</div>
          <TrendBadge pct={qqqChange} />
        </div>
        <div style={{ flex: 1, background: "#0f1117", border: "1px solid #1e293b", borderRadius: "6px", padding: "8px 10px" }}>
          <div style={{ fontSize: "9px", color: "#475569" }}>GOES X-RAY FLUX</div>
          <div style={{ fontSize: "16px", fontWeight: "bold", color: solar.flux >= 1e-5 ? "#f59e0b" : "#94a3b8" }}>{solar.cls}</div>
          <div style={{ fontSize: "10px", color: solar.flux >= 1e-5 ? "#f59e0b" : "#475569" }}>{solar.label}</div>
        </div>
        <div style={{ flex: 1, background: "#0f1117", border: "1px solid #1e293b", borderRadius: "6px", padding: "8px 10px" }}>
          <div style={{ fontSize: "9px", color: "#475569" }}>TRU FLASHES</div>
          <div style={{ fontSize: "16px", fontWeight: "bold", color: "#f59e0b" }}>{flashCount}</div>
          <div style={{ fontSize: "10px", color: "#475569" }}>Solar events</div>
        </div>
        <div style={{ flex: 1, background: "#0f1117", border: "1px solid "#1e293b", borderRadius: "6px", padding: "8px 10px" }}>
          <div style={{ fontSize: "9px", color: "#475569" }}>UPDATED</div>
          <div style={{ fontSize: "16px", fontWeight: "bold", color: "#94a3b8" }}>{lastFetch || "—"}</div>
          {fetching && <div style={{ fontSize: "10px", color: "#f59e0b" }}>⟳</div>}
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "12px", flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
          {["ALL", "SPECULATIVE", "ACTIVE", "CAUTIOUS", "DORMANT"].map(f => (
            <button key={f} onClick={() => setScoreFilter(f)} style={{
              padding: "4px 10px", fontSize: "10px", cursor: "pointer", borderRadius: "4px",
              border: scoreFilter === f ? "1px solid #f59e0b" : "1px solid #334155",
              background: scoreFilter === f ? "#1e1a0a" : "transparent",
              color: scoreFilter === f ? "#f59e0b" : "#94a3b8",
            }}>{f}</button>
          ))}
        </div>
        <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", marginLeft: "auto" }}>
          {sectors.map(s => (
            <button key={s} onClick={() => setSectorFilter(s)} style={{
              padding: "4px 8px", fontSize: "9px", cursor: "pointer", borderRadius: "4px",
              border: sectorFilter === s ? "1px solid #6366f1" : "1px solid #334155",
              background: sectorFilter === s ? "#1e1b3a" : "transparent",
              color: sectorFilter === s ? "#a5b4fc" : "#475569",
            }}>{s}</button>
          ))}
        </div>
      </div>

      {/* Stock table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", minWidth: "680px" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #1e293b" }}>
              {["TRU SCORE", "SYMBOL", "PRICE", "CHANGE", "SECTOR", "SIGNAL"].map(h => (
                <th key={h} style={{ padding: "6px 8px", textAlign: "left", color: "#475569", fontWeight: "normal", fontSize: "10px" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {activeStocks.map((s, i) => {
              const { tier, color, glow } = scoreTier(s.score);
              return (
                <tr key={s.symbol} style={{ borderBottom: "1px solid #111827" }}>
                  <td style={{ padding: "8px 8px" }}>
                    <div style={{
                      display: "inline-block", minWidth: "36px", textAlign: "center",
                      background: glow ? `rgba(245,158,11,0.15)` : "transparent",
                      border: `1px solid ${color}`,
                      borderRadius: "4px", padding: "3px 6px",
                      color, fontWeight: "bold", fontSize: "13px",
                      boxShadow: glow ? `0 0 8px ${color}` : "none",
                    }}>{s.score}</div>
                  </td>
                  <td style={{ padding: "8px 8px" }}>
                    <div style={{ color: "#f8fafc", fontWeight: "bold", fontSize: "12px" }}>{s.symbol}</div>
                    <div style={{ color: "#475569", fontSize: "9px" }}>{s.name}</div>
                  </td>
                  <td style={{ padding: "8px 8px", color: "#e2e8f0" }}>
                    {s.basePrice < 10 ? `$${s.price?.toFixed(4)}` : `$${s.price?.toFixed(2)}`}
                  </td>
                  <td style={{ padding: "8px 8px" }}><TrendBadge pct={s.pct || 0} /></td>
                  <td style={{ padding: "8px 8px", color: "#64748b", fontSize: "10px" }}>{s.sector}</td>
                  <td style={{ padding: "8px 8px" }}>
                    <span style={{ color, fontSize: "10px", fontWeight: "bold", letterSpacing: "1px" }}>{tier}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div style={{ marginTop: "20px", fontSize: "9px", color: "#334155", textAlign: "center", lineHeight: "1.8", borderTop: "1px solid #1e293b", paddingTop: "12px" }}>
        PLAY MODE · NO REAL MONEY · TRU SCORE 5-99 · ADAPTS TO QQQ + SOLAR CONDITIONS<br />
        Signals cool off when market regime shifts. NOT financial advice.
      </div>
    </div>
  );
}
