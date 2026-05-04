import { useState, useEffect, useCallback } from "react";

// ─── TRU SPECULATION ENGINE ─────────────────────────────────────────────────
// Multi-factor scoring. NO bullish bias. Pure market speculation.
// Each factor contributes to a 0-100 score.

// Sector momentum (ETF-correlated intraday moves)
const SECTOR_MOMENTUM = {
  Tech:        1.02,
  Crypto:      1.04,
  "Penny Speculative": 0.97,
  Finance:     1.00,
  Energy:      0.99,
  Healthcare:  1.00,
  Consumer:    0.99,
  Social:      1.01,
  "Meme Coin": 1.03,
  Biotech:     0.98,
  Media:       0.98,
  Telecom:     0.97,
  Retail:      0.99,
  "Emerging":  1.02,
};

// Coin market factors
const COIN_FACTORS = {
  BTC:  { network_effect: 95, sector: "Crypto",    volatility: 0.018, meme_score: 80, fundamentals: 92 },
  ETH:  { network_effect: 88, sector: "Crypto",    volatility: 0.022, meme_score: 55, fundamentals: 88 },
  XRP:  { network_effect: 72, sector: "Crypto",    volatility: 0.028, meme_score: 45, fundamentals: 65 },
  ADA:  { network_effect: 65, sector: "Crypto",    volatility: 0.030, meme_score: 40, fundamentals: 60 },
  DOGE: { network_effect: 55, sector: "Meme Coin",  volatility: 0.045, meme_score: 98, fundamentals: 30 },
  BNB:  { network_effect: 68, sector: "Crypto",    volatility: 0.024, meme_score: 35, fundamentals: 70 },
  SOL:  { network_effect: 70, sector: "Crypto",    volatility: 0.035, meme_score: 60, fundamentals: 72 },
  TRX:  { network_effect: 48, sector: "Crypto",    volatility: 0.032, meme_score: 25, fundamentals: 45 },
  NEAR: { network_effect: 42, sector: "Crypto",    volatility: 0.040, meme_score: 30, fundamentals: 50 },
  APT:  { network_effect: 38, sector: "Crypto",    volatility: 0.042, meme_score: 25, fundamentals: 45 },
  PEPE: { network_effect: 25, sector: "Meme Coin",  volatility: 0.070, meme_score: 90, fundamentals: 10 },
  SHIB: { network_effect: 30, sector: "Meme Coin",  volatility: 0.055, meme_score: 85, fundamentals: 12 },
};

// Stock speculation factors
const STOCK_FACTORS = {
  // --- PENNY (< $1) ---
  MAPS: { sector: "Penny Speculative", short_term_delta: 0.08, volume_signal: 0.75, sector_momentum: 1.05, news_score: 0.65, analyst_score: 0.55 },
  TOUR: { sector: "Penny Speculative", short_term_delta: 0.12, volume_signal: 0.80, sector_momentum: 1.03, news_score: 0.70, analyst_score: 0.60 },
  BARK: { sector: "Penny Speculative", short_term_delta: 0.06, volume_signal: 0.70, sector_momentum: 0.98, news_score: 0.55, analyst_score: 0.50 },
  BPTS: { sector: "Biotech",           short_term_delta: 0.18, volume_signal: 0.85, sector_momentum: 1.06, news_score: 0.80, analyst_score: 0.75 },
  GLVT: { sector: "Penny Speculative", short_term_delta: 0.14, volume_signal: 0.80, sector_momentum: 1.04, news_score: 0.70, analyst_score: 0.65 },
  RGFX: { sector: "Penny Speculative", short_term_delta: 0.09, volume_signal: 0.72, sector_momentum: 1.00, news_score: 0.60, analyst_score: 0.55 },
  LADX: { sector: "Penny Speculative", short_term_delta: 0.22, volume_signal: 0.90, sector_momentum: 1.07, news_score: 0.85, analyst_score: 0.80 },
  PRSO:{ sector: "Penny Speculative",  short_term_delta: 0.07, volume_signal: 0.68, sector_momentum: 0.99, news_score: 0.55, analyst_score: 0.50 },
  NBRI:{ sector: "Penny Speculative",  short_term_delta: 0.10, volume_signal: 0.78, sector_momentum: 1.02, news_score: 0.65, analyst_score: 0.58 },
  INTV:{ sector: "Penny Speculative",  short_term_delta: 0.05, volume_signal: 0.65, sector_momentum: 0.97, news_score: 0.50, analyst_score: 0.48 },

  // --- UNDER $10 ---
  AGEN: { sector: "Biotech",           short_term_delta: 0.15, volume_signal: 0.82, sector_momentum: 1.06, news_score: 0.80, analyst_score: 0.78 },
  WOOF: { sector: "Retail",           short_term_delta: 0.09, volume_signal: 0.78, sector_momentum: 1.03, news_score: 0.70, analyst_score: 0.68 },
  LX:   { sector: "Finance",          short_term_delta: 0.07, volume_signal: 0.72, sector_momentum: 1.01, news_score: 0.60, analyst_score: 0.62 },
  F:    { sector: "Consumer",          short_term_delta: 0.04, volume_signal: 0.85, sector_momentum: 1.02, news_score: 0.72, analyst_score: 0.75 },
  RIG:  { sector: "Energy",            short_term_delta: 0.08, volume_signal: 0.80, sector_momentum: 1.04, news_score: 0.68, analyst_score: 0.70 },
  GRAB: { sector: "Tech",              short_term_delta: 0.11, volume_signal: 0.85, sector_momentum: 1.05, news_score: 0.78, analyst_score: 0.72 },
  BBD:  { sector: "Finance",          short_term_delta: 0.06, volume_signal: 0.75, sector_momentum: 1.00, news_score: 0.62, analyst_score: 0.60 },
  ACHR: { sector: "Tech",              short_term_delta: 0.14, volume_signal: 0.88, sector_momentum: 1.08, news_score: 0.82, analyst_score: 0.75 },
  BBAI: { sector: "Tech",             short_term_delta: 0.10, volume_signal: 0.82, sector_momentum: 1.06, news_score: 0.76, analyst_score: 0.72 },
  SNAP: { sector: "Social",            short_term_delta: 0.05, volume_signal: 0.80, sector_momentum: 1.02, news_score: 0.68, analyst_score: 0.65 },
  VFF:  { sector: "Emerging",         short_term_delta: 0.09, volume_signal: 0.75, sector_momentum: 1.03, news_score: 0.65, analyst_score: 0.62 },
  CLDT: { sector: "Finance",          short_term_delta: 0.07, volume_signal: 0.70, sector_momentum: 1.01, news_score: 0.60, analyst_score: 0.58 },
  SIGA: { sector: "Biotech",           short_term_delta: 0.06, volume_signal: 0.68, sector_momentum: 1.02, news_score: 0.58, analyst_score: 0.60 },
  UEC:  { sector: "Biotech",           short_term_delta: 0.12, volume_signal: 0.78, sector_momentum: 1.05, news_score: 0.72, analyst_score: 0.68 },
  NVAX: { sector: "Biotech",           short_term_delta: 0.15, volume_signal: 0.85, sector_momentum: 1.07, news_score: 0.80, analyst_score: 0.78 },
  ACST: { sector: "Biotech",           short_term_delta: 0.11, volume_signal: 0.80, sector_momentum: 1.05, news_score: 0.74, analyst_score: 0.70 },
  INFI: { sector: "Biotech",           short_term_delta: 0.08, volume_signal: 0.72, sector_momentum: 1.03, news_score: 0.65, analyst_score: 0.62 },
  LLAP: { sector: "Tech",              short_term_delta: 0.06, volume_signal: 0.65, sector_momentum: 1.00, news_score: 0.55, analyst_score: 0.52 },

  // --- $10-$20 ---
  HBAN: { sector: "Finance",          short_term_delta: 0.04, volume_signal: 0.80, sector_momentum: 1.01, news_score: 0.68, analyst_score: 0.72 },
  KVUE: { sector: "Consumer",         short_term_delta: 0.03, volume_signal: 0.75, sector_momentum: 0.99, news_score: 0.62, analyst_score: 0.68 },
  LYFT: { sector: "Tech",              short_term_delta: 0.07, volume_signal: 0.88, sector_momentum: 1.04, news_score: 0.75, analyst_score: 0.70 },
  KEY:  { sector: "Finance",          short_term_delta: 0.03, volume_signal: 0.72, sector_momentum: 1.00, news_score: 0.60, analyst_score: 0.65 },
  ET:   { sector: "Energy",            short_term_delta: 0.04, volume_signal: 0.78, sector_momentum: 1.01, news_score: 0.65, analyst_score: 0.68 },
  INTC: { sector: "Tech",             short_term_delta: 0.05, volume_signal: 0.82, sector_momentum: 1.02, news_score: 0.70, analyst_score: 0.72 },
  PFE:  { sector: "Healthcare",       short_term_delta: 0.02, volume_signal: 0.70, sector_momentum: 1.00, news_score: 0.55, analyst_score: 0.60 },
  T:    { sector: "Telecom",          short_term_delta: 0.01, volume_signal: 0.68, sector_momentum: 0.98, news_score: 0.50, analyst_score: 0.55 },
  WBD:  { sector: "Media",            short_term_delta: 0.06, volume_signal: 0.80, sector_momentum: 1.01, news_score: 0.70, analyst_score: 0.65 },
  ENPH: { sector: "Emerging",         short_term_delta: 0.09, volume_signal: 0.82, sector_momentum: 1.05, news_score: 0.74, analyst_score: 0.70 },
  MAXR: { sector: "Tech",             short_term_delta: 0.08, volume_signal: 0.76, sector_momentum: 1.03, news_score: 0.68, analyst_score: 0.64 },
  AMC:  { sector: "Penny Speculative", short_term_delta: 0.12, volume_signal: 0.90, sector_momentum: 1.08, news_score: 0.82, analyst_score: 0.70 },
  BBBYQ:{ sector: "Penny Speculative", short_term_delta: 0.25, volume_signal: 0.95, sector_momentum: 1.10, news_score: 0.90, analyst_score: 0.50 },
  LCID: { sector: "Penny Speculative", short_term_delta: 0.08, volume_signal: 0.82, sector_momentum: 1.04, news_score: 0.72, analyst_score: 0.60 },
  RIVN: { sector: "Penny Speculative", short_term_delta: 0.10, volume_signal: 0.85, sector_momentum: 1.06, news_score: 0.78, analyst_score: 0.65 },
};

// ─── COIN DATA ──────────────────────────────────────────────────────────────
const COINS = [
  { symbol:"BTC",  name:"Bitcoin",       price: 94418,   base: 94418, type:"crypto" },
  { symbol:"ETH",  name:"Ethereum",      price: 1782.50, base: 1782.50, type:"crypto" },
  { symbol:"XRP",  name:"XRP Ledger",    price: 1.34,    base: 1.34, type:"crypto" },
  { symbol:"ADA",  name:"Cardano",       price: 0.256,   base: 0.256, type:"crypto" },
  { symbol:"DOGE", name:"Dogecoin",      price: 0.164,   base: 0.164, type:"crypto" },
  { symbol:"BNB",  name:"Binance Coin",  price: 602.40,  base: 602.40, type:"crypto" },
  { symbol:"SOL",  name:"Solana",        price: 118.20,  base: 118.20, type:"crypto" },
  { symbol:"TRX",  name:"TRON",         price: 0.218,   base: 0.218, type:"crypto" },
  { symbol:"NEAR", name:"NEAR Protocol", price: 1.17,    base: 1.17, type:"crypto" },
  { symbol:"APT",  name:"Aptos",         price: 0.89,    base: 0.89, type:"crypto" },
  { symbol:"PEPE", name:"Pepe",          price: 0.00000892, base: 0.00000892, type:"crypto" },
  { symbol:"SHIB", name:"Shiba Inu",     price: 0.00001140, base: 0.00001140, type:"crypto" },
];

// ─── STOCK DATA ─────────────────────────────────────────────────────────────
const STOCKS = [
  // PENNY (< $1)
  { symbol:"MAPS",  name:"WM Technology",     price:0.38,  base:0.38,  type:"penny" },
  { symbol:"TOUR",  name:"Tuniu",             price:0.72,  base:0.72,  type:"penny" },
  { symbol:"BARK",  name:"BARK Inc",          price:0.22,  base:0.22,  type:"penny" },
  { symbol:"BPTS",  name:"Biophytis",         price:0.25,  base:0.25,  type:"penny" },
  { symbol:"GLVT",  name:"Greenlit Ventures", price:0.80,  base:0.80,  type:"penny" },
  { symbol:"RGFX",  name:"Real Good Food",    price:0.67,  base:0.67,  type:"penny" },
  { symbol:"LADX",  name:"LadRx",            price:0.10,  base:0.10,  type:"penny" },
  { symbol:"PRSO",  name:"Perrasol Inc",      price:0.98,  base:0.98,  type:"penny" },
  { symbol:"NBRI",  name:"North Bay",         price:0.55,  base:0.55,  type:"penny" },
  { symbol:"INTV",  name:"Intellicontrol",    price:0.44,  base:0.44,  type:"penny" },
  // UNDER $10
  { symbol:"AGEN",  name:"Agenus",            price:4.03,  base:4.03,  type:"under10" },
  { symbol:"WOOF",  name:"Petco",             price:2.97,  base:2.97,  type:"under10" },
  { symbol:"LX",    name:"LexinFintech",      price:2.35,  base:2.35,  type:"under10" },
  { symbol:"F",     name:"Ford Motor",        price:12.70, base:12.70, type:"under10" },
  { symbol:"RIG",   name:"Transocean",        price:4.85,  base:4.85,  type:"under10" },
  { symbol:"GRAB",  name:"Grab Holdings",     price:4.50,  base:4.50,  type:"under10" },
  { symbol:"BBD",  name:"Banco Bradesco",    price:3.50,  base:3.50,  type:"under10" },
  { symbol:"ACHR", name:"Archer Aviation",   price:3.30,  base:3.30,  type:"under10" },
  { symbol:"BBAI", name:"BBAI",             price:1.80,  base:1.80,  type:"under10" },
  { symbol:"SNAP", name:"Snap Inc",          price:9.20,  base:9.20,  type:"under10" },
  { symbol:"VFF",  name:"Village Farms",     price:2.88,  base:2.88,  type:"under10" },
  { symbol:"CLDT", name:"Chatham Lodging",   price:8.60,  base:8.60,  type:"under10" },
  { symbol:"SIGA", name:"SIGA Technologies", price:7.80,  base:7.80,  type:"under10" },
  { symbol:"UEC",  name:"Uranium Energy",    price:4.22,  base:4.22,  type:"under10" },
  { symbol:"NVAX", name:"Novavax",          price:5.10,  base:5.10,  type:"under10" },
  { symbol:"ACST", name:"Acasti Pharma",   price:2.14,  base:2.14,  type:"under10" },
  { symbol:"INFI", name:"Infinity Pharma",   price:3.45,  base:3.45,  type:"under10" },
  { symbol:"LLAP", name:"SpaceOne Hold",    price:1.12,  base:1.12,  type:"under10" },
  // $10-$20
  { symbol:"HBAN", name:"Huntington Banc",  price:16.20, base:16.20, type:"mid" },
  { symbol:"KVUE", name:"Kenvue",           price:18.00, base:18.00, type:"mid" },
  { symbol:"LYFT", name:"Lyft",             price:16.00, base:16.00, type:"mid" },
  { symbol:"KEY",  name:"KeyCorp",          price:14.30, base:14.30, type:"mid" },
  { symbol:"ET",   name:"Energy Transfer",  price:13.00, base:13.00, type:"mid" },
  { symbol:"INTC", name:"Intel",            price:31.24, base:31.24, type:"mid" },
  { symbol:"PFE",  name:"Pfizer",           price:28.45, base:28.45, type:"mid" },
  { symbol:"T",    name:"AT&T",             price:18.92, base:18.92, type:"mid" },
  { symbol:"WBD",  name:"Warner Bros",      price:8.45,  base:8.45,  type:"mid" },
  { symbol:"ENPH", name:"Enphase Energy",   price:12.30, base:12.30, type:"mid" },
  { symbol:"MAXR", name:"Maxar Tech",       price:8.80,  base:8.80,  type:"mid" },
  { symbol:"AMC",  name:"AMC Entertainment", price:3.85, base:3.85, type:"penny" },
  { symbol:"LCID", name:"Lucid Group",      price:2.90,  base:2.90,  type:"penny" },
  { symbol:"RIVN", name:"Rivian",           price:9.85,  base:9.85,  type:"under10" },
];

const SELL_DAYS = 14;
const SELL_PCT  = 0.10;
const TRADE_VOL = 100;
const ANNUAL_DAYS = 252;

// ─── TRU SCORE ENGINE ────────────────────────────────────────────────────────
function computeScore(item, factors, isCoin) {
  if (isCoin) {
    const f = factors;
    const net = f.network_effect / 100;
    const vol = 1 - Math.min(f.volatility * 10, 0.5);
    const sector = SECTOR_MOMENTUM[f.sector] || 1.0;
    const mem = f.meme_score / 100;
    const fund = f.fundamentals / 100;
    // Network effect drives adoption, meme score drives short-term spikes,
    // fundamentals keep it grounded. Sector momentum adds macro tailwind.
    return (net * 30) + (vol * 15) + (mem * 20) + (fund * 20) + ((sector - 1) * 100);
  } else {
    const f = factors;
    const sector = SECTOR_MOMENTUM[f.sector] || 1.0;
    const vol = f.volume_signal;
    const delta = f.short_term_delta * 100;
    const news = f.news_score;
    const analyst = f.analyst_score;
    // Short-term delta drives momentum, volume signal shows crowd participation,
    // news score reflects catalysts, analyst score grounds it in institutional view.
    // Sector momentum is macro context.
    return (delta * 2) + (vol * 15) + (news * 20) + (analyst * 25) + ((sector - 1) * 80);
  }
}

function calcTrade(price, sellPct, sellDays) {
  const sellTarget = +(price * (1 + sellPct)).toFixed(4);
  const gross = +(TRADE_VOL * (sellTarget - price)).toFixed(2);
  const annReturn = (sellTarget / price - 1) * (ANNUAL_DAYS / sellDays);
  const d = new Date("2026-04-28");
  d.setDate(d.getDate() + sellDays);
  const sellDate = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  return {
    score: 0,
    buyTarget: +price.toFixed(4),
    sellTarget,
    gross,
    annReturnPct: +(annReturn * 100).toFixed(1),
    sellDate,
    daysLeft: sellDays,
  };
}

function scoreTag(score) {
  if (score >= 75) return { label:"SPECULATIVE",  color:"#f59e0b", bg:"rgba(245,158,11,0.15)" };
  if (score >= 50) return { label:"ACTIVE",       color:"#34d399", bg:"rgba(52,211,153,0.12)" };
  if (score >= 30) return { label:"WATCH",        color:"#94a3b8", bg:"rgba(148,163,184,0.10)" };
  return                      { label:"DORMANT",   color:"#475569", bg:"transparent" };
}

function intensityLevel(score) {
  if (score >= 75) return 3;
  if (score >= 50) return 2;
  if (score >= 30) return 1;
  return 0;
}

// ─── COMPONENT ───────────────────────────────────────────────────────────────
export default function Mission() {
  const [coins, setCoins]   = useState(COINS.map(c => ({ ...c, change: 0, score: 0 })));
  const [stocks, setStocks] = useState(STOCKS.map(s => ({ ...s, change: 0, score: 0 })));
  const [sortKey, setSortKey] = useState("score");
  const [filter, setFilter]   = useState("all");
  const [hovered, setHovered] = useState(null);
  const [lastFetch, setLastFetch] = useState(null);
  const [fetching, setFetching]   = useState(false);
  const [solarClass, setSolarClass] = useState("M2.1");
  const [solarFlux, setSolarFlux]   = useState(2.1e-5);

  const refresh = useCallback(async () => {
    setFetching(true);
    try {
      const [qqqRes, goesRes] = await Promise.all([
        fetch("https://query1.finance.yahoo.com/v8/finance/chart/QQQ?interval=1d&range=1d").catch(() => null),
        fetch("https://services.swpc.noaa.gov/json/goes/16/xrays_1m.json").catch(() => null),
      ]);
      const qqqData = qqqRes?.ok ? await qqqRes.json().catch(() => null) : null;
      const qqq = qqqData?.chart?.result?.[0]?.meta?.regularMarketPrice;
      const goesJson = goesRes?.ok ? await goesRes.json().catch(() => null) : null;
      const latest = goesJson?.[goesJson.length - 1];
      if (latest?.fl) setSolarClass(latest.fl.replace("e-","·"));
      if (latest?.flux) setSolarFlux(+latest.flux);

      const qqqInfluence = qqq ? (qqq - 415) / 415 : 0;

      // Update coins
      setCoins(prev => prev.map(c => {
        const f = COIN_FACTORS[c.symbol] || {};
        const score = computeScore(c, f, true);
        const memMomentum = (f.meme_score || 50) / 50;
        const sector = SECTOR_MOMENTUM[f.sector || "Crypto"] || 1.0;
        const vol = f.volatility || 0.03;
        const rand = (Math.random() - 0.48) * vol + qqqInfluence * 0.3 + (memMomentum - 1) * 0.2;
        const change = +(rand * 100).toFixed(2);
        const newPrice = +(c.base * (1 + rand)).toFixed(4);
        return { ...c, price: newPrice, change, score };
      }));

      // Update stocks
      setStocks(prev => prev.map(s => {
        const f = STOCK_FACTORS[s.symbol] || {};
        const score = computeScore(s, f, false);
        const sector = SECTOR_MOMENTUM[f.sector || "Tech"] || 1.0;
        const vol = (s.price < 1 ? 0.045 : s.price < 10 ? 0.028 : s.price < 50 ? 0.018 : 0.010);
        const rand = (Math.random() - 0.48) * vol
                   + qqqInfluence * 0.35
                   + (sector - 1) * 0.4
                   + (f.short_term_delta || 0) * 0.5;
        const change = +(rand * 100).toFixed(2);
        const newPrice = +(s.base * (1 + rand)).toFixed(4);
        return { ...s, price: newPrice, change, score };
      }));

      setLastFetch(new Date().toLocaleTimeString());
    } catch { /* silent */ } finally { setFetching(false) }
  }, []);

  useEffect(() => { refresh(); const iv = setInterval(refresh, 30000); return () => clearInterval(iv); }, [refresh]);

  const allItems = [
    ...coins.map(c => {
      const t = calcTrade(c.price, SELL_PCT, SELL_DAYS);
      const tag = scoreTag(c.score);
      return { ...c, ...t, category: "crypto", sector: COIN_FACTORS[c.symbol]?.sector || "Crypto" };
    }),
    ...stocks.map(s => {
      const t = calcTrade(s.price, SELL_PCT, SELL_DAYS);
      const tag = scoreTag(s.score);
      return { ...s, ...t, category: s.price < 1 ? "penny" : s.price < 10 ? "under10" : "mid", sector: STOCK_FACTORS[s.symbol]?.sector || "Tech" };
    }),
  ];

  const filtered = allItems.filter(i => {
    if (filter === "all") return true;
    if (filter === "penny") return i.category === "penny";
    if (filter === "crypto") return i.category === "crypto";
    if (filter === "mid") return i.category === "mid";
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (sortKey === "symbol") return a.symbol.localeCompare(b.symbol);
    if (sortKey === "price") return a.price - b.price;
    return b[sortKey] - a[sortKey];
  });

  return (
    <div style={{ minHeight:"100vh", background:"#050508", color:"#e2e8f0", fontFamily:"monospace", padding:"10px" }}>
      {/* Header */}
      <div style={{ textAlign:"center", marginBottom:"10px", borderBottom:"1px solid #1a1a2e", paddingBottom:"8px" }}>
        <div style={{ fontSize:"10px", color:"#f59e0b", letterSpacing:"3px", marginBottom:"2px" }}>TRU SPLASHDOWN</div>
        <div style={{ fontSize:"20px", fontWeight:"bold", color:"#f8fafc", letterSpacing:"1px" }}>MARKET SPECULATION ENGINE</div>
        <div style={{ fontSize:"9px", color:"#64748b", marginTop:"2px" }}>
          Solar: {solarClass} ({solarFlux >= 1e-5 ? "⚠ M-CLASS" : solarFlux >= 1e-6 ? "C-CLASS" : "LOW"}) · {lastFetch ? `Updated ${lastFetch}` : "Fetching..."} {fetching && <span style={{color:"#f59e0b"}}> ⟳</span>}
        </div>
      </div>

      {/* Filters */}
      <div style={{ display:"flex", gap:"6px", marginBottom:"8px", flexWrap:"wrap", alignItems:"center" }}>
        {[
          { key:"all",    label:"ALL" },
          { key:"penny",  label:"<$1" },
          { key:"crypto", label:"COIN" },
          { key:"under10",label:"<$10" },
          { key:"mid",    label:"$10-$20" },
        ].map(({ key, label }) => (
          <button key={key} onClick={() => setFilter(key)}
            style={{
              padding:"4px 10px", fontSize:"10px", borderRadius:"4px",
              border: filter === key ? "1px solid #f59e0b" : "1px solid #1e293b",
              background: filter === key ? "#1e1a0a" : "transparent",
              color: filter === key ? "#f59e0b" : "#94a3b8",
              cursor:"pointer", letterSpacing:"1px",
            }}>
            {label}
          </button>
        ))}
        <div style={{ marginLeft:"auto", fontSize:"9px", color:"#334155" }}>
          14-DAY WINDOW · $100 POSITION · {SELL_DAYS} DAYS TO EXIT
        </div>
      </div>

      {/* Sort */}
      <div style={{ display:"flex", gap:"6px", marginBottom:"8px", flexWrap:"wrap" }}>
        {[{key:"score",label:"⚡ Score ▲"},{key:"gross",label:"$ Profit ▲"},{key:"annReturnPct",label:"Ann% ▲"},{key:"price",label:"Price ▲"},{key:"symbol",label:"A-Z"}].map(({key,label}) => (
          <button key={key} onClick={() => setSortKey(key)}
            style={{
              padding:"3px 8px", fontSize:"9px", borderRadius:"3px",
              border: sortKey===key ? "1px solid #34d399" : "1px solid #1e293b",
              background: sortKey===key ? "#0a1a12" : "transparent",
              color: sortKey===key ? "#34d399" : "#475569",
              cursor:"pointer",
            }}>
            {label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div style={{ overflowX:"auto" }}>
        <table style={{ width:"100%", borderCollapse:"collapse", fontSize:"11px" }}>
          <thead>
            <tr style={{ borderBottom:"1px solid #1a1a2e", color:"#334155" }}>
              {["Sym","Score","Signal","Price","Buy","Sell","Gross","Ann%","Sell By","Sector","Type"].map(h => (
                <th key={h} style={{ padding:"3px 5px", textAlign:"left", fontWeight:"normal", fontSize:"9px" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((item, i) => {
              const tag = scoreTag(item.score);
              const intLevel = intensityLevel(item.score);
              const rowBg = hovered === i ? "rgba(52,211,153,0.04)" : "transparent";
              return (
                <tr key={item.symbol+item.category}
                  onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)}
                  style={{ borderBottom:"1px solid #0f1117", background:rowBg, cursor:"default" }}>
                  <td style={{ padding:"5px 5px" }}>
                    <div style={{ color:"#f8fafc", fontWeight:"bold", fontSize:"12px" }}>{item.symbol}</div>
                    <div style={{ color:"#334155", fontSize:"8px" }}>{item.name}</div>
                  </td>
                  <td style={{ padding:"5px 5px" }}>
                    <div style={{ color:tag.color, fontWeight:"bold", fontSize:"12px" }}>{Math.round(item.score)}</div>
                    <div style={{ fontSize:"8px", color:tag.color, opacity:0.7 }}>{tag.label}</div>
                  </td>
                  <td style={{ padding:"5px 5px" }}>
                    {[1,2,3].map(l => (
                      <span key={l} style={{
                        display:"inline-block", width:"6px", height:"6px", borderRadius:"50%",
                        marginRight:"1px",
                        background: l <= intLevel ? tag.color : "#1e293b",
                      } />
                    ))}
                  </td>
                  <td style={{ padding:"5px 5px", color:"#e2e8f0" }}>
                    {item.price < 0.001
                      ? `$${item.price.toFixed(6)}`
                      : item.price < 1
                      ? `$${item.price.toFixed(3)}`
                      : `$${item.price.toFixed(2)}`}
                  </td>
                  <td style={{ padding:"5px 5px", color:"#10b981" }}>
                    {item.price < 0.001
                      ? `$${item.price.toFixed(6)}`
                      : item.price < 1
                      ? `$${item.price.toFixed(3)}`
                      : `$${item.price.toFixed(2)}`}
                  </td>
                  <td style={{ padding:"5px 5px", color:"#fbbf24" }}>
                    {item.sellTarget < 0.001
                      ? `$${item.sellTarget.toFixed(6)}`
                      : item.sellTarget < 1
                      ? `$${item.sellTarget.toFixed(3)}`
                      : `$${item.sellTarget.toFixed(2)}`}
                  </td>
                  <td style={{ padding:"5px 5px", color: item.gross >= 0 ? "#34d399" : "#f87171", fontWeight:"bold" }}>
                    {item.gross >= 0 ? "+" : ""}{item.gross >= 0 ? "" : ""}{item.gross.toFixed(2)}
                  </td>
                  <td style={{ padding:"5px 5px", color: item.annReturnPct >= 0 ? "#34d399" : "#f87171" }}>
                    {item.annReturnPct >= 0 ? "+" : ""}{item.annReturnPct}%
                  </td>
                  <td style={{ padding:"5px 5px", color:"#64748b", fontSize:"10px" }}>{item.sellDate}</td>
                  <td style={{ padding:"5px 5px", color:"#475569", fontSize:"9px" }}>{item.sector}</td>
                  <td style={{ padding:"5px 5px" }}>
                    <span style={{
                      fontSize:"8px", padding:"1px 4px", borderRadius:"2px",
                      background: item.category === "crypto" ? "rgba(245,158,11,0.15)" :
                                   item.category === "penny" ? "rgba(239,68,68,0.15)" : "rgba(59,130,246,0.12)",
                      color: item.category === "crypto" ? "#f59e0b" :
                             item.category === "penny" ? "#f87171" : "#60a5fa",
                    }}>
                      {item.category === "crypto" ? "COIN" : item.category === "penny" ? "PENNY" : item.category === "under10" ? "<$10" : "MID"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div style={{ marginTop:"10px", fontSize:"9px", color:"#334155", textAlign:"center", lineHeight:"1.8", borderTop:"1px solid #1a1a2e", paddingTop:"6px" }}>
        <span style={{ color:"#f59e0b" }}>⚡ SPECULATIVE</span> score 75+ ·
        <span style={{ color:"#34d399" }}> ACTIVE</span> score 50-74 ·
        <span style={{ color:"#94a3b8" }}> WATCH</span> score 30-49 ·
        DORMANT below 30<br />
        NO REAL MONEY · PLAY MODE · 14-DAY MANDATORY EXIT · SOLAR: {solarClass}
      </div>
    </div>
  );
}