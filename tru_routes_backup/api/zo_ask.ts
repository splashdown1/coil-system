export default async (c) => {
  let input = "";
  try { const body = await c.req.json().catch(() => null); if (body) input = body.input || body.message || ""; } catch { input = ""; }
  if (!input) return c.json({ output: "Tru is silent. No input." }, 400);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 110000);
  try {
    const res = await fetch("https://api.zo.computer/zo/ask", {
      method: "POST",
      headers: { "Authorization": `Bearer ${process.env.ZO_CLIENT_IDENTITY_TOKEN}`, "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ input, model_name: "vercel:minimax/minimax-m2.7" }),
      signal: controller.signal,
    });
    clearTimeout(timer);
    const data = await res.json().catch(() => ({ output: "Tru is silent" }));
    return c.json({ output: data.output || "Tru is silent" });
  } catch (e) {
    clearTimeout(timer);
    return c.json({ output: "Tru is silent" }, 502);
  }
};
