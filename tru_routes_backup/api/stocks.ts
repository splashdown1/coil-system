import type { Context } from "hono";
import { AI } from "@ zo.ai";
export default async (c: Context) => {
  const { input, model_name } = await c.req.json<{ input: string; model_name?: string }>();
  try {
    const res = await fetch("https://api.zo.computer/zo/ask", { method: "POST", headers: { "Authorization": `Bearer ${process.env.ZO_CLIENT_IDENTITY_TOKEN}`, "Content-Type": "application/json" }, body: JSON.stringify({ input, model_name: model_name || "vercel:minimax/minimax-m2.7" }) });
    const data = await res.json();
    return c.json(data);
  } catch (err) { return c.json({ error: "Bridge error" }, 500); }
};
