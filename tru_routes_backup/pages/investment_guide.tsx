export default function InvestmentGuide() {
  return (
    <div style={{ minHeight:"100vh",background:"#0a0a0f",color:"#e0e0e0",fontFamily:"monospace",padding:"2rem" }}>
      <div style={{ maxWidth:900,margin:"0 auto" }}>
        <div style={{ display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:32 }}>
          <h1 style={{ fontSize:"1.5rem",fontWeight:700,color:"#00ff88" }}>INVESTMENT THESIS</h1>
          <a href="/" style={{ color:"#888",textDecoration:"none" }}>← Tru</a>
        </div>
        <div style={{ background:"#0f1510",border:"1px solid #00ff8833",padding:20,marginBottom:28 }}>
          <h2 style={{ color:"#00ff88",marginBottom:8 }}>SOLAR CYCLE 25</h2>
          <p style={{ color:"#aaa",fontSize:"0.85rem",lineHeight:1.6 }}>Peak activity predicted <strong style={{color:"#fff"}}>2024–2026</strong> — coincides with the 4-year election cycle. Historically correlates with increased speculative activity.</p>
        </div>
        <div style={{ overflowX:"auto" }}>
          <table style={{ width:"100%",borderCollapse:"collapse",fontSize:"0.75rem" }}>
            <thead><tr style={{ borderBottom:"2px solid #00ff88" }}>{["ASSET","SECTOR","SIGNAL","SCORE","ENTRY","DATE"].map(h => <th key={h} style={{ padding:"8px 6px",color:"#00ff88",textAlign:"left" }}>{h}</th>)}</tr></thead>
            <tbody>{[["NVDA","Technology","Momentum","92","$118","2025-04-01"],["AAPL","Technology","Breakout","88","$212","2025-04-01"],["MSFT","Technology","Momentum","85","$415","2025-04-01"],["GOOG","Technology","Breakout","82","$178","2025-04-01"],["META","Technology","Momentum","80","$530","2025-04-01"],["TSLA","Consumer","Reversal","65","$180","2025-04-01"],["JPM","Financial","Dividend","78","$195","2025-04-01"],["GS","Financial","Value","75","$450","2025-04-01"],["AV","Financial","Growth","82","$145","2025-04-01"],["BLK","Financial","Dividend","80","$820","2025-04-01"],["UNH","Healthcare","Growth","76","$520","2025-04-01"],["LLY","Healthcare","Growth","82","$760","2025-04-01"],["ABBV","Healthcare","Dividend","74","$175","2025-04-01"],["REGN","Healthcare","Pipeline","88","$920","2025-04-01"],["VRTX","Healthcare","Pipeline","85","$430","2025-04-01"],["WMT","Consumer","Dividend","72","$68","2025-04-01"],["KO","Consumer","Dividend","70","$62","2025-04-01"],["PEP","Consumer","Dividend","68","$172","2025-04-01"],["HD","Consumer","Momentum","74","$360","2025-04-01"],["NEE","Utilities","Growth","82","$72","2025-04-01"],["CAT","Industrials","Momentum","74","$340","2025-04-01"],["HON","Industrials","Dividend","72","$195","2025-04-01"],["UPS","Industrials","Value","70","$138","2025-04-01"],["NKE","Consumer","Reversal","68","$78","2025-04-01"],["AMZN","Technology","Momentum","88","$195","2025-04-01"],["COST","Consumer","Dividend","75","$740","2025-04-01"]].map(([asset,sector,signal,score,entry,date]) => (<tr key={asset} style={{ borderBottom:"1px solid #1a1a1a" }}><td style={{ padding:"8px 6px",color:"#fff",fontWeight:700 }}>{asset}</td><td style={{ padding:"8px 6px",color:"#666" }}>{sector}</td><td style={{ padding:"8px 6px",color:"#00ff88" }}>{signal}</td><td style={{ padding:"8px 6px",color:parseInt(score)>=80?"#00ff88":parseInt(score)>=70?"#ffaa00":"#ff4444" }}>{score}</td><td style={{ padding:"8px 6px",color:"#aaa" }}>{entry}</td><td style={{ padding:"8px 6px",color:"#555" }}>{date}</td></tr>))}</tbody>
          </table>
        </div>
        <div style={{ marginTop:28,padding:"12px 16px",background:"#111",border:"1px solid #333",fontSize:"0.7rem",color:"#666" }}>Signal types: <strong style={{color:"#fff"}}>Momentum</strong> = trend following · <strong style={{color:"#fff"}}>Breakout</strong> = resistance breakout · <strong style={{color:"#fff"}}>Reversal</strong> = mean reversion · <strong style={{color:"#fff"}}>Dividend</strong> = income focused · <strong style={{color:"#fff"}}>Value</strong> = intrinsic discount · <strong style={{color:"#fff"}}>Growth</strong> = earnings expansion</div>
      </div>
    </div>
  );
}
