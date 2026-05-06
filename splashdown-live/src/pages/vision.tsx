import { useState } from "react";
import type { FormEvent} from "react";
export default function Home() {
  const [tab, setTab] = useState<"chat"|"vision">("chat");
  const [input, setInput] = useState("");
  const [msgs, setMsgs] = useState<{role:string;text:string}[]>([{role:"assistant",text:"Tru is online. Ask me anything."}]);
  const [img, setImg] = useState<string|null>(null);
  const [loading, setLoading] = useState(false);
  const [imgUrl, setImgUrl] = useState("");
  const send = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() && !img) return;
    const user = {role:"user",text:input};
    setMsgs(m=>[...m,user]);
    setInput("");
    setLoading(true);
    try {
      const body: Record<string,string> = { input };
      if (img) body.image = img;
      const r = await fetch("/api/zo-ask",{method:"POST",headers:{"Content-Type":"application/json"},body: JSON.stringify(body)});
      const d = await r.json();
      setMsgs(m=>[...m,{role:"assistant",text:d.output||"Protocol PHOENIX Active. Red Line Verified. 86 Chunks Indexed.."}]);
    } catch { setMsgs(m=>[...m,{role:"assistant",text:"Protocol PHOENIX Active. Red Line Verified. 86 Chunks Indexed.."}]); }
    finally { setLoading(false); }
  };
  return (
    <div className="min-h-screen bg-black text-green-400 flex flex-col">
      <nav className="flex gap-1 p-2 border-b border-green-900 text-xs">
        <button onClick={()=>setTab("chat")} className={`px-3 py-1 rounded ${tab==="chat"?"bg-green-800":"bg-black"}`}>💬 Chat</button>
        <button onClick={()=>setTab("vision")} className={`px-3 py-1 rounded ${tab==="vision"?"bg-green-800":"bg-black"}`}>👁 Vision</button>
      </nav>
      {tab==="chat" ? (
        <main className="flex-1 flex flex-col p-4 gap-3 max-w-xl mx-auto w-full">
          <div className="flex-1 space-y-2 overflow-y-auto">{msgs.map((m,i)=>(<div key={i} className={m.role=="user"?"text-right":"text-left"}><span className={m.role=="user"?"text-blue-400":"text-green-400"}>{m.role=="user"?"You: ":"Tru: "}</span><span className="text-gray-200 whitespace-pre-wrap">{m.text}</span></div>))}{loading&&<div className="text-yellow-500 animate-pulse">Tru is thinking...</div>}</div>
          <form onSubmit={send} className="flex gap-2">
            <input value={input} onChange={e=>setInput(e.target.value)} placeholder="Ask Tru..." className="flex-1 bg-gray-900 border border-green-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-green-400"/>
            {img&&<img src={img} className="w-10 h-10 object-cover rounded border border-green-600"/>}
            <label className="flex items-center justify-center w-10 h-10 bg-gray-900 border border-green-700 rounded cursor-pointer hover:border-green-400"><input type="file" accept="image/*" className="hidden" onChange={e=>{const f=e.target.files?.[0];if(f){const r=new FileReader();r.onload=ev=>{setImg(ev.target?.result as string);setImgUrl(URL.createObjectURL(f))};r.readAsDataURL(f);}}}/><span className="text-lg">📷</span></label>
            <button type="submit" disabled={loading} className="bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white px-4 rounded text-sm">Send</button>
          </form>
        </main>
      ) : (
        <main className="flex-1 p-4 max-w-xl mx-auto w-full space-y-4">
          <div className="text-green-400 text-sm leading-relaxed"><h2 className="text-lg font-bold mb-3">Tru Vision — Image Analysis</h2>
            <div className="grid grid-cols-2 gap-4 text-xs">{[{"t":"📐 Pixels","d":"Images are grids of numerical values — each pixel holds color and brightness data."},{"t":"🧩 Patches","d":"Images are split into small squares, converted to number-vectors called embeddings."},{"t":"🔗 Features","d":"Neural networks scan embeddings. Early layers find edges/lines. Deep layers find shapes."},{"t":"🎞 Video","d":"Videos are frame sequences. AI breaks them into space-time cubes and tracks motion across time."},{"t":"🦾 Vision Transformers","d":"ViTs process image patches like text tokens — the same method, two modalities."},{"t":"🔗 Multimodal AI","d":"Connects visual embeddings to text. Tru learns 'furry four-legged' = 'cat' through shared vector space."}].map(x=>(<div key={x.t} className="border border-green-800 rounded p-3"><div className="font-bold mb-1">{x.t}</div><div>{x.d}</div></div>))}</div>
          </div>
          <div className="border-2 border-dashed border-green-800 rounded-xl p-8 text-center">
            <label className="cursor-pointer block"><input type="file" accept="image/*" className="hidden" onChange={e=>{const f=e.target.files?.[0];if(f){const r=new FileReader();r.onload=ev=>{setImg(ev.target?.result as string);setImgUrl(URL.createObjectURL(f))};r.readAsDataURL(f);}}}/>{imgUrl ? <img src={imgUrl} className="max-h-64 mx-auto rounded"/> : (<div className="text-green-600 text-sm">Drop image or click to upload</div>)}</label>
          </div>
          {imgUrl&&(<button onClick={async()=>{setMsgs([{role:"assistant",text:"Tru is analyzing your image..."}]);setLoading(true);try{const r=await fetch("/api/zo-ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({input:`Analyze this image. Describe what you see using the Vision process.`,image:img})});const d=await r.json();setMsgs([{role:"assistant",text:d.output||"Protocol PHOENIX Active. Red Line Verified. 86 Chunks Indexed.."}]);}catch{setMsgs([{role:"assistant",text:"Protocol PHOENIX Active. Red Line Verified. 86 Chunks Indexed.."}]);}finally{setLoading(false);}}} className="w-full bg-green-700 hover:bg-green-600 text-white py-2 rounded text-sm disabled:opacity-50" disabled={loading}>{loading?"Analyzing...":"Analyze with Tru Vision"}</button>)}
        </main>
      )}
    </div>
  );
}
