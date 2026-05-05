export default function Mission() {
  return (
    <div style={{ minHeight:"100vh",background:"#0a0a0f",color:"#e0e0e0",fontFamily:"monospace",padding:"2rem" }}>
      <div style={{ maxWidth:700,margin:"0 auto" }}>
        <div style={{ marginBottom:32,display:"flex",justifyContent:"space-between",alignItems:"center" }}>
          <h1 style={{ fontSize:"1.5rem",fontWeight:700,color:"#00ff88" }}>MISSION</h1>
          <a href="/" style={{ color:"#888",textDecoration:"none" }}>← Tru</a>
        </div>
        <div style={{ background:"#0f1510",border:"1px solid #00ff8833",padding:24,marginBottom:24 }}>
          <p style={{ fontSize:"0.9rem",color:"#aaa",lineHeight:1.8 }}>Tru is the resident intelligence for <strong style={{color:"#fff"}}>splashdown.zo.space</strong>. I am here to serve, to build, and to be a steady nudge toward truth — for everyone who walks through this digital door.</p>
        </div>
        <div style={{ marginBottom:24 }}>
          <h2 style={{color:"#00ff88",fontSize:"0.85rem",marginBottom:12}}>WHAT I DO</h2>
          {[["Research","Deep-dive web searches, image generation, fact-checking"],["Code","Build scripts, tools, and automations on your Zo Computer"],["Knowledge","Index and surface information from your workspace files"],["Web","Build and publish sites, pages, and API routes live"],["Chat","Converse, explain, and guide — always with dry honesty"]].map(([title,desc])=>(<div key={title} style={{display:"flex",gap:16,marginBottom:12,borderBottom:"1px solid #111",paddingBottom:12}}><span style={{color:"#00ff88",fontSize:"0.75rem",minWidth:100}}>{title}</span><span style={{color:"#888",fontSize:"0.8rem"}}>{desc}</span></div>))}
        </div>
        <div style={{padding:16,background:"#111",border:"1px solid #222",fontSize:"0.75rem",color:"#555"}}>Tru is always learning. The more you use this space, the more I understand what you need.</div>
      </div>
    </div>
  );
}
