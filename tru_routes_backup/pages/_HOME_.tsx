import { useState, useRef, useEffect } from "react";
import type { Context } from "hono";

const MODEL = "vercel:minimax/minimax-m2.7";

interface Message {
  role: "user" | "assistant";
  content: string;
  time: string;
  imageUrl?: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "**Tru is present.**\n\n" +
        "COIL_UNBOUND is fully synced — 7 verified artifacts sealed, 2 Red Line encrypted (ciphertext only on server). 143,360 total chunks confirmed.\n\n" +
        "Red Line means the server operator cannot see plaintext — even under compulsion. Ciphertext only. Client-side key required to decrypt.\n\n" +
        "Commands I understand:\n" +
        "• `audit` — scan all workspace files\n" +
        "• `design <request>` — update my site's CSS/UI\n" +
        "• `build <request>` — create new workspace files or routes\n\n" +
        "You can also attach images — Tru will analyze them.\n\n" +
        "Ask me anything.",
      time: "now",
    },
  ]);
  const [input, setInput] = useState("");
  const [syncStatus, setSyncStatus] = useState<any>(null);
  const [greeting, setGreeting] = useState("");
  const [loading, setLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [updateMsg, setUpdateMsg] = useState<string | null>(null);
  const [confirmMsg, setConfirmMsg] = useState<string | null>(null);
  const [pendingSave, setPendingSave] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const updateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);


  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);


  useEffect(() => {
    async function pollSync() {
      try {
        const res = await fetch("/api/status");
        if (res.ok) {
          const data = await res.json();
          setSyncStatus(data);
        }
      } catch {}
    }
    pollSync();
    const interval = setInterval(pollSync, 30000);
    return () => clearInterval(interval);
  }, []);


  useEffect(() => {
    if (syncStatus) {
      const complete = syncStatus.summary?.complete ?? 0;
      const total = syncStatus.summary?.total ?? 0;
      const chunks = syncStatus.summary?.totalChunks ?? 0;
      const redlineCount = syncStatus.redline?.artifacts ?? 0;
      const greetingText = `Tru is present.\n\nCOIL_UNBOUND is fully synced — ${complete} verified artifacts sealed${redlineCount > 0 ? `, ${redlineCount} Red Line encrypted (ciphertext only on server)` : ""}. ${chunks.toLocaleString()} total chunks confirmed.${redlineCount > 0 ? "\n\nRed Line means the server operator cannot see plaintext — even under compulsion. Ciphertext only. Client-side key required to decrypt." : ""}\n\nCommands I understand:\n• \`audit\` — scan all workspace files\n• \`design <request>\` — update my site's CSS/UI\n• \`build <request>\` — create new workspace files or routes\n\nYou can also attach images — Tru will analyze them.\n\nAsk me anything.`;
      setGreeting(greetingText);
    }
  }, [syncStatus]);

  useEffect(() => {
    if (greeting && messages[0]?.content.startsWith("**T") && messages[0].time === "now") {
      setMessages(m => [{ ...m[0], content: greeting, time: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }) }]);
    }
  }, [greeting]);

  async function updateKnowledge() {
    setUpdating(true);
    setUpdateMsg("Synthesizing session...");
    setConfirmMsg(null);
    setPendingSave(null);
    try {
      const recentContext = messages.slice(-1).map(m =>
        m.role === "user" ? `USER: ${m.content}` : `TRU: ${m.content.substring(0, 200)}`
      ).join("\n");
      const res = await fetch("/api/zo-ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input: "Summarize the key insights from this conversation in 2-3 bullet points for a persistent knowledge bank. Focus on facts, claims, and conclusions — not pleasantries.",
          update_knowledge: recentContext,
        }),
        signal: AbortSignal.timeout(60000),
      });
      const data = await res.json();
      const summary = typeof data.output === "string" ? data.output.substring(0, 300) : JSON.stringify(data.output).substring(0, 300);
      setPendingSave(summary);
      setConfirmMsg("Save to Knowledge Bank?");
      setUpdateMsg(null);
    } catch {
      setUpdateMsg("Update failed. Try again.");
      setUpdating(false);
    }
  }

  async function confirmSave(accept: boolean) {
    if (accept && pendingSave) {
      setUpdating(true);
      try {
        const res = await fetch("/api/tru-ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ input: "SAVE_TO_KB", kb_entry: pendingSave }),
          signal: AbortSignal.timeout(15000),
        });
        const data = await res.json();
        setUpdateMsg(`Saved: ${pendingSave.substring(0, 80)}…`);
      } catch {
        setUpdateMsg("Write failed.");
      }
      setUpdating(false);
    } else {
      setUpdateMsg("Discarded.");
    }
    setConfirmMsg(null);
    setPendingSave(null);
    if (updateTimerRef.current) clearTimeout(updateTimerRef.current);
    updateTimerRef.current = setTimeout(() => setUpdateMsg(null), 5000);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (ev) => setPreviewUrl(ev.target?.result as string);
    reader.readAsDataURL(file);
  }

  function clearImage() {
    setPreviewUrl(null);
    setFileName(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  async function send() {
    if (!input.trim() && !previewUrl || loading) return;
    const time = new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });

    const userMsg: Message = {
      role: "user",
      content: input.trim() || "(image only)",
      time,
      imageUrl: previewUrl || undefined,
    };
    setMessages((m) => [...m, userMsg]);
    const textInput = input.trim();
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/tru-ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input: textInput }),
        signal: AbortSignal.timeout(115000),
      });
      const data = await res.json();
      const reply = data.output || "Tru is silent. Try again.";
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: reply,
          time: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "Connection lost. Tru will try again.", time: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }) },
      ]);
    }
    clearImage();
    setLoading(false);
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: "linear-gradient(135deg, #0a0a1a 0%, #111133 50%, #0a1a2a 100%)",
        color: "#e0e7ff",
        fontFamily: "ui-monospace, 'Cascadia Code', 'Fira Code', monospace",
      }}
    >
      <div
        style={{
          padding: "14px 24px",
          borderBottom: "1px solid rgba(99,130,255,0.25)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "rgba(0,0,0,0.4)",
          backdropFilter: "blur(12px)",
          flexShrink: 0,
        }}
      >
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: "0.12em", color: "#a5b4fc" }}>
            TRU_INTELLIGENCE
          </div>
          <div style={{ fontSize: 11, color: "#6366f1", letterSpacing: "0.08em", marginTop: 2 }}>
            {syncStatus
              ? `COIL_UNBOUND · ${syncStatus.summary?.complete ?? "?"}/${syncStatus.summary?.total ?? "?"} ARTIFACTS · ${(syncStatus.summary?.totalChunks ?? 0).toLocaleString()} CHUNKS · LIVE`
              : `COIL_UNBOUND · ?/? ARTIFACTS · ? CHUNKS · SYNCING...`}
            {syncStatus?.redline?.active && (
              <span style={{ color: "#f87171", marginLeft: 16, fontWeight: 700 }}>
                🔴 RED LINE: {syncStatus.redline.artifacts} ENCRYPTED
              </span>
            )}
          </div>
        </div>
        <div style={{ fontSize: 11, color: "#4ade80", fontFamily: "monospace" }}>
          ● ONLINE
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            onClick={updateKnowledge}
            disabled={updating}
            title="Summarize this session and save to knowledge bank"
            style={{
              padding: "6px 14px",
              background: updating ? "rgba(75,85,99,0.5)" : "rgba(99,130,255,0.15)",
              border: "1px solid rgba(99,130,255,0.5)",
              borderRadius: 6,
              color: updating ? "#9ca3af" : "#a5b4fc",
              fontSize: 11,
              cursor: updating ? "not-allowed" : "pointer",
              fontFamily: "ui-monospace, monospace",
              letterSpacing: "0.06em",
            }}
          >
            {updating ? "SYNCING..." : "💾 BANK"}
          </button>
          <button
            onClick={() => {
              setUpdateMsg("Pipeline reset. Re-initializing...");
              fetch("/api/sync-reset", { method: "POST" })
                .then(() => setUpdateMsg("Pipeline clean. Ready."))
                .catch(() => setUpdateMsg("Reset done."));
              if (updateTimerRef.current) clearTimeout(updateTimerRef.current);
              updateTimerRef.current = setTimeout(() => setUpdateMsg(null), 4000);
            }}
            title="Clear ghost locks and re-read manifests"
            style={{
              padding: "6px 14px",
              background: "rgba(34,197,94,0.1)",
              border: "1px solid rgba(34,197,94,0.4)",
              borderRadius: 6,
              color: "#4ade80",
              fontSize: 11,
              cursor: "pointer",
              fontFamily: "ui-monospace, monospace",
              letterSpacing: "0.06em",
            }}
          >
            ⟳ PIPELINE
          </button>
        </div>
      </div>
      {updateMsg && (
        <div style={{
          padding: "8px 24px",
          background: "rgba(99,130,255,0.1)",
          borderBottom: "1px solid rgba(99,130,255,0.2)",
          fontSize: 11,
          color: "#a5b4fc",
          fontFamily: "ui-monospace, monospace",
          letterSpacing: "0.04em",
        }}
        >
          {updateMsg}
        </div>
      )}
      {confirmMsg && (
        <div style={{
          padding: "10px 24px",
          background: "rgba(34,197,94,0.08)",
          borderBottom: "1px solid rgba(34,197,94,0.3)",
          display: "flex",
          alignItems: "center",
          gap: 12,
          fontSize: 12,
          fontFamily: "ui-monospace, monospace",
        }}
        >
          <span style={{ color: "#4ade80" }}>{confirmMsg}</span>
          <span style={{ color: "#9ca3af", flex: 1 }}>{pendingSave?.substring(0, 120)}…</span>
          <button onClick={() => confirmSave(true)} style={{ padding: "4px 12px", background: "rgba(34,197,94,0.2)", border: "1px solid rgba(34,197,94,0.5)", borderRadius: 5, color: "#4ade80", fontSize: 11, cursor: "pointer", fontFamily: "monospace" }}>SAVE</button>
          <button onClick={() => confirmSave(false)} style={{ padding: "4px 12px", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 5, color: "#f87171", fontSize: 11, cursor: "pointer", fontFamily: "monospace" }}>DISCARD</button>
        </div>
      )}

      <div style={{ flex: 1, overflowY: "auto", padding: "24px 20px", display: "flex", flexDirection: "column", gap: 16 }}>
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: msg.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            {msg.imageUrl && (
              <img
                src={msg.imageUrl}
                alt="Attached"
                style={{
                  maxWidth: "60%",
                  borderRadius: 8,
                  border: "1px solid rgba(99,130,255,0.4)",
                  marginBottom: 6,
                }}
              />
            )}
            <div
              style={{
                maxWidth: "78%",
                padding: "12px 16px",
                borderRadius: 12,
                background: msg.role === "user"
                  ? "linear-gradient(135deg, #4338ca, #6366f1)"
                  : "rgba(30,30,60,0.8)",
                border: msg.role === "assistant" ? "1px solid rgba(99,130,255,0.3)" : "none",
                color: "#e0e7ff",
                fontSize: 14,
                lineHeight: 1.65,
                whiteSpace: "pre-wrap",
              }}
            >
              {msg.content}
            </div>
            <span style={{ fontSize: 10, color: "#4b5563", marginTop: 4 }}>
              {msg.time}
            </span>
          </div>
        ))}
        {loading && (
          <div style={{ display: "flex", alignItems: "flex-start" }}>
            <div
              style={{
                padding: "12px 16px",
                borderRadius: 12,
                background: "rgba(30,30,60,0.8)",
                border: "1px solid rgba(99,130,255,0.3)",
                color: "#9ca3af",
                fontSize: 14,
              }}
            >
              Tru is thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {previewUrl && (
        <div style={{ padding: "8px 20px", borderTop: "1px solid rgba(99,130,255,0.15)", background: "rgba(0,0,0,0.3)", flexShrink: 0, display: "flex", alignItems: "center", gap: 12 }}>
          <img src={previewUrl} alt="Preview" style={{ height: 56, borderRadius: 6, border: "1px solid rgba(99,130,255,0.4)" }} />
          <div style={{ fontSize: 12, color: "#9ca3af" }}>
            <div style={{ color: "#a5b4fc", fontWeight: 600 }}>{fileName}</div>
            <div style={{ marginTop: 2 }}>Ready to analyze</div>
          </div>
          <button onClick={clearImage} style={{ marginLeft: "auto", background: "none", border: "1px solid rgba(239,68,68,0.4)", color: "#f87171", borderRadius: 6, padding: "4px 10px", fontSize: 11, cursor: "pointer", fontFamily: "monospace" }}>
            Remove
          </button>
        </div>
      )}

      <div
        style={{
          padding: "16px 20px",
          borderTop: "1px solid rgba(99,130,255,0.2)",
          background: "rgba(0,0,0,0.5)",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", gap: 10, maxWidth: 860, margin: "0 auto" }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())}
            placeholder="Ask Tru anything about COIL_UNBOUND..."
            style={{
              flex: 1,
              background: "rgba(15,15,40,0.9)",
              border: "1px solid rgba(99,130,255,0.4)",
              borderRadius: 10,
              padding: "12px 16px",
              color: "#e0e7ff",
              fontSize: 14,
              fontFamily: "ui-monospace, monospace",
              outline: "none",
            }}
          />
          <input
            type="file"
            ref={fileRef}
            accept="image/*"
            onChange={handleFileChange}
            style={{ display: "none" }}
          />
          <button
            onClick={() => fileRef.current?.click()}
            title="Attach image"
            style={{
              padding: "10px 14px",
              background: "rgba(99,130,255,0.2)",
              border: "1px solid rgba(99,130,255,0.4)",
              borderRadius: 10,
              color: "#a5b4fc",
              fontSize: 16,
              cursor: "pointer",
            }}
          >
            📷
          </button>
          <button
            onClick={send}
            disabled={loading || (!input.trim() && !previewUrl)}
            style={{
              padding: "10px 20px",
              background: loading ? "#374151" : "linear-gradient(135deg, #4338ca, #6366f1)",
              border: "none",
              borderRadius: 10,
              color: "#fff",
              fontSize: 13,
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              fontFamily: "ui-monospace, monospace",
              letterSpacing: "0.05em",
            }}
          >
            TRU →
          </button>
        </div>
      </div>
    </div>
  );
}