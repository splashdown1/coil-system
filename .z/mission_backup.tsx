import { useState, useEffect, useRef, useCallback } from "react";

const REAL_STOCKS = [
  { symbol: "AAPL",  name: "Apple",                    sector: "Tech",        price: 214.29, base: 214.29 },
  { symbol: "MSFT",  name: "Microsoft",                sector: "Tech",        price: 415.50, base: 415.50 },
  { symbol: "GOOGL", name: "Alphabet",                 sector: "Tech",        price: 175.98, base: 175.98 },
  { symbol: "NVDA",  name: "NVIDIA",                   sector: "Tech",        price: 875.39, base: 875.39 },
  { symbol: "AMZN",  name: "Amazon",                   sector: "Consumer",    price: 198.12, base: 198.12 },
  { symbol: "META",  name: "Meta",                     sector: "Social",      price: 565.89, base: 565.89 },
  { symbol: "BRK.B", name: "Berkshire Hathaway",       sector: "Finance",     price: 394.50, base: 394.50 },
  { symbol: "JPM",   name: "JPMorgan",                 sector: "Finance",     price: 212.75, base: 212.75 },
  { symbol: "V",    name: "Visa",                      sector: "Finance",     price: 276.30, base: 276.30 },
  { symbol: "JNJ",  name: "Johnson & Johnson",         sector: "Healthcare",  price: 152.88, base: 152.88 },
  { symbol: "UNH",  name: "UnitedHealth",              sector: "Healthcare",  price: 524.60, base: 524.60 },
  { symbol: "XOM",  name: "Exxon Mobil",              sector: "Energy",      price: 108.74, base: 108.74 },
  { symbol: "AVGO", name: "Broadcom",                  sector: "Tech",        price: 144.50, base: 144.50 },
  { symbol: "PG",   name: "Procter & Gamble",          sector: "Consumer",    price: 168.30, base: 168.30 },
  { symbol: "MA",   name: "Mastercard",                sector: "Finance",     price: 488.20, base: 488.20 },
  { symbol: "HD",   name: "Home Depot",               sector: "Retail",      price: 352.80, base: 352.80 },
  { symbol: "CVX",  name: "Chevron",                  sector: "Energy",      price: 149.25, base: 149.25 },
  { symbol: "ABBV", name: "AbbVie",                   sector: "Healthcare",  price: 194.80, base: 194.80 },
  { symbol: "MRK",  name: "Merck",                    sector: "Healthcare",  price: 118.40, base: 118.40 },
  { symbol: "LLY",  name: "Eli Lilly",               sector: "Healthcare",  price: 812.50, base: 812.50 },
  { symbol: "KO",   name: "Coca-Cola",                sector: "Consumer",    price: 62.15,  base: 62.15  },
  { symbol: "PEP",  name: "PepsiCo",                   sector: "Consumer",    price: 168.90, base: 168.90 },
  { symbol: "COST", name: "Costco",                   sector: "Retail",      price: 912.40, base: 912.40 },
  { symbol: "TMO",  name: "Thermo Fisher",            sector: "Healthcare",  price: 548.70, base: 548.70 },
  { symbol: "WMT",  name: "Walmart",                 sector: "Retail",       price: 68.35,  base: 68.35  },
  { symbol: "BAC",  name: "Bank of America",          sector: "Finance",     price: 42.18,  base: 42.18  },
  { symbol: "DIS",  name: "Walt Disney",              sector: "Media",       price: 112.40, base: 112.40 },
  { symbol: "VZ",   name: "Verizon",                  sector: "Telecom",     price: 41.85,  base: 41.85  },
  { symbol: "INTC", name: "Intel",                   sector: "Tech",        price: 31.24,  base: 31.24  },
  { symbol: "CRM",  name: "Salesforce",               sector: "Tech",        price: 298.75, base: 298.75 },
  { symbol: "AMD",  name: "AMD",                      sector: "Tech",        price: 178.30, base: 178.30 },
  { symbol: "PFE",  name: "Pfizer",                  sector: "Healthcare",  price: 28.45,  base: 28.45  },
  { symbol: "T",    name: "AT&T",                    sector: "Telecom",     price: 18.92,  base: 18.92  },
  { symbol: "NKE",  name: "Nike",                    sector: "Consumer",    price: 93.40,  base: 93.40  },
  { symbol: "MCD",  name: "McDonald's",               sector: "Consumer",    price: 492.80, base: 492.80 },
  { symbol: "GS",   name: "Goldman Sachs",            sector: "Finance",     price: 512.40, base: 512.40 },
  { symbol: "MS",   name: "Morgan Stanley",          sector: "Finance",     price: 98.75,  base: 98.75  },
  { symbol: "CSCO", name: "Cisco",                    sector: "Tech",        price: 52.30,  base: 52.30  },
  { symbol: "ADBE", name: "Adobe",                    sector: "Tech",        price: 475.20, base: 475.20 },
  { symbol: "ACN",  name: "Accenture",               sector: "Tech",        price: 368.90, base: 368.90 },
];

const BULLISH_BIAS = 0.30;
const SELL_DAYS = 14;
const SELL_PCT  = 0.12;
const TRADE_VOLUME = 100;
const ANNUAL_TRADING_DAYS = 252;

function estimateSellDate() {
  const d = new Date("2026-04-28");
  d.setDate(d.getDate() + SELL_DAYS);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function calcTrade(stock) {
  const sellTarget = +(stock.price * (1 + SELL_PCT + BULLISH_BIAS)).toFixed(2);
  const gross = +(TRADE_VOLUME * (sellTarget - stock.price)).toFixed(2);
  const annReturn = (sellTarget / stock.price - 1) * (ANNUAL_TRADING_DAYS / SELL_DAYS);
  return {
    sellTarget,
    grossProfit: gross,
    annReturnPct: +(annReturn * 100).toFixed(1),
    sellDate: estimateSellDate(),
  };
}

function TrendArrow({ pct }) {
  const up = pct > 0;
  const col = up ? "text-green-400" : "text-red-400";
  return (
    <span className={`font-bold ${col}`}>
      {up ? "▲" : "▼"} {Math.abs(pct).toFixed(2)}%
    </span>
  );
}

export default function Mission() {
  const [stocks, setStocks]   = useState(REAL_STOCKS.map(s => ({ ...s, change: 0 })));
  const [sortKey, setSortKey] = useState("grossProfit");
  const [hovered, setHovered] = useState(null);
  const [lastFetch, setLastFetch] = useState(null);
  const [fetching, setFetching] = useState(false);
  const [solarClass, setSolarClass] = useState("C6.2");
  const [solarFlux, setSolarFlux]   = useState(6.2e-6);
  const [flashCount, setFlashCount] = useState(0);

  const fetchLive = useCallback(async () => {
    setFetching(true);
    try {
      const [qqqRes, goesRes] = await Promise.all([
        fetch("https://query1.finance.yahoo.com/v8/finance/chart/QQQ?interval=1d&range=1d"),
        fetch("https://services.swpc.noaa.gov/json/goes/16/xrays_1m.json").catch(() => null),
      ]);
      const qqqData = qqqRes.ok ? await qqqRes.json().catch(() => null) : null;
      const qqq = qqqData?.chart?.result?.[0]?.meta?.regularMarketPrice;
      const goes = goesRes?.ok ? await goesRes.json().catch(() => null) : null;
      const latest = goes?.[goes.length - 1];

      setLastFetch(new Date().toLocaleTimeString());
      setSolarClass(latest?.fl?.replace("e-", "·") || solarClass);
      setSolarFlux(latest?.flux ? +latest.flux : solarFlux);

      setStocks(prev => prev.map(s => {
        if (!qqq) return s;
        const base = s.base;
        const influence = (qqq - 415) / 415;
        const vol = base < 50 ? 0.038 : base < 200 ? 0.025 : 0.015;
        const rand = (Math.random() - 0.49) * vol + influence * 0.4;
        const change = +(rand * 100).toFixed(2);
        const newPrice = +(base * (1 + rand)).toFixed(2);
        return { ...s, price: newPrice, change };
      }));
    } catch { /* silent */ } finally { setFetching(false) }
  }, []);

  useEffect(() => {
    fetchLive();
    const iv = setInterval(fetchLive, 30000);
    return () => clearInterval(iv);
  }, [fetchLive]);

  const sorted = [...stocks].sort((a, b) => {
    if (sortKey === "symbol") return a.symbol.localeCompare(b.symbol);
    return (calcTrade(b)[sortKey] - calcTrade(a)[sortKey]);
  });

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0f", color: "#e2e8f0", fontFamily: "monospace", padding: "12px" }}>
      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: "10px" }}>
        <div style={{ fontSize: "11px", color: "#f59e0b", letterSpacing: "2px" }}>TRU SPLASHDOWN</div>
        <div style={{ fontSize: "22px", fontWeight: "bold", color: "#f8fafc", letterSpacing: "1px" }}>
          COIL MARKET SIMULATOR
        </div>
        <div style={{ fontSize: "10px", color: "#64748b" }}>
          Solar: {solarClass} | QQQ LIVE | {lastFetch ? `Updated ${lastFetch}` : "Fetching..."} {fetching && <span style={{ color: "#f59e0b" }}>⟳</span>}
        </div>
      </div>

      {/* Sort bar */}
      <div style={{ display: "flex", gap: "6px", marginBottom: "10px", flexWrap: "wrap" }}>
        {[
          { key: "grossProfit",  label: "Profit ▲" },
          { key: "annReturnPct",label: "Annual ▲" },
          { key: "sellTarget",  label: "Target ▲" },
          { key: "price",       label: "Price ▲" },
          { key: "symbol",      label: "A-Z" },
        ].map(({ key, label }) => (
          <button key={key} onClick={() => setSortKey(key)}
            style={{
              padding: "4px 10px", fontSize: "10px", borderRadius: "4px",
              border: sortKey === key ? "1px solid #f59e0b" : "1px solid #334155",
              background: sortKey === key ? "#1e1a0a" : "transparent",
              color: sortKey === key ? "#f59e0b" : "#94a3b8", cursor: "pointer",
            }}>
            {label}
          </button>
        ))}
        <div style={{ marginLeft: "auto", fontSize: "10px", color: "#475569", alignSelf: "center" }}>
          14-DAY TRADE · BULLISH BIAS {+(BULLISH_BIAS*100)}% · ${TRADE_VOLUME}/TRADE
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #1e293b", color: "#475569" }}>
              {["Symbol","Price","Change","Buy Target","Sell Target","Gross","Ann %","Sell By","Sector"].map(h => (
                <th key={h} style={{ padding: "4px 6px", textAlign: "left", fontWeight: "normal" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((s, i) => {
              const { sellTarget, grossProfit, annReturnPct, sellDate } = calcTrade(s);
              const rowBg = hovered === i ? "#131a28" : "transparent";
              return (
                <tr key={s.symbol} onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)}
                  style={{ borderBottom: "1px solid #111827", background: rowBg, cursor: "default" }}>
                  <td style={{ padding: "5px 6px" }}>
                    <div style={{ color: "#f8fafc", fontWeight: "bold" }}>{s.symbol}</div>
                    <div style={{ color: "#475569", fontSize: "9px" }}>{s.name}</div>
                  </td>
                  <td style={{ padding: "5px 6px", color: "#e2e8f0" }}>${s.price.toFixed(2)}</td>
                  <td style={{ padding: "5px 6px" }}><TrendArrow pct={s.change} /></td>
                  <td style={{ padding: "5px 6px", color: "#10b981" }}>${s.price.toFixed(2)}</td>
                  <td style={{ padding: "5px 6px", color: "#fbbf24" }}>${sellTarget.toFixed(2)}</td>
                  <td style={{ padding: "5px 6px", color: grossProfit >= 0 ? "#34d399" : "#f87171", fontWeight: "bold" }}>
                    {grossProfit >= 0 ? "+" : ""}${grossProfit.toFixed(2)}
                  </td>
                  <td style={{ padding: "5px 6px", color: annReturnPct >= 0 ? "#34d399" : "#f87171" }}>
                    {annReturnPct >= 0 ? "+" : ""}{annReturnPct}%
                  </td>
                  <td style={{ padding: "5px 6px", color: "#94a3b8" }}>{sellDate}</td>
                  <td style={{ padding: "5px 6px", color: "#64748b" }}>{s.sector}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div style={{ marginTop: "14px", fontSize: "9px", color: "#334155", textAlign: "center", lineHeight: "1.6" }}>
        PLAY MODE · NO REAL MONEY · BULLISH {+(BULLISH_BIAS*100)}% · 14-DAY TRADE WINDOW · {SELL_DAYS} DAYS TO SELL<br />
        Solar X-Ray: {solarClass} ({solarFlux >= 1e-5 ? "⚠ M-CLASS" : solarFlux >= 1e-6 ? "C-CLASS" : "LOW"}) · Market prices update every 30 seconds
      </div>
    </div>
  );
}
