const express = require("express");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const zlib = require("zlib");

const app = express();
const PORT = 3000;
const UPLOAD_DIR = "./uploads";
const MANIFESTS_DIR = "./manifests";
const DATA_DIR = "./data";
const PATCHES_DIR = "./patches";

[UPLOAD_DIR, MANIFESTS_DIR, DATA_DIR, PATCHES_DIR].forEach(dir => {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

// ─── HELPERS ───────────────────────────────────────────────────────────────

function readManifest(fileId) {
  const manifestPath = path.join(MANIFESTS_DIR, `${fileId}.json`);
  if (fs.existsSync(manifestPath)) {
    return JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  }
  return null;
}

function writeManifest(fileId, manifest) {
  const manifestPath = path.join(MANIFESTS_DIR, `${fileId}.json`);
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
}

async function verifyChunkHash(data, expectedHash) {
  const actualHash = crypto.createHash("sha256").update(data).digest("hex");
  if (actualHash !== expectedHash) {
    console.log(`[VERIFY] ❌ expected=${expectedHash} actual=${actualHash}`);
  }
  return actualHash === expectedHash;
}

async function decompressChunk(data) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    const inflate = zlib.createInflate();
    inflate.on("data", chunk => chunks.push(chunk));
    inflate.on("end", () => resolve(Buffer.concat(chunks)));
    inflate.on("error", reject);
    inflate.write(data);
    inflate.end();
  });
}

// ─── PATCH ENGINE (RFC 6902) ─────────────────────────────────────────────

function applyPatch(obj, ops) {
  const result = JSON.parse(JSON.stringify(obj)); // deep clone
  for (const op of ops) {
    const keys = op.path.split("/").filter(k => k !== "");
    const lastKey = keys[keys.length - 1];
    let target = result;
    for (let i = 0; i < keys.length - 1; i++) {
      if (!(keys[i] in target)) target[keys[i]] = {};
      target = target[keys[i]];
    }
    if (op.op === "remove") {
      delete target[lastKey];
    } else if (op.op === "replace" || op.op === "add") {
      target[lastKey] = op.value;
    }
  }
  return result;
}

// ─── BODY HELPERS ────────────────────────────────────────────────────────

function readBody(req, limitMB = 50) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on("data", chunk => {
      size += chunk.length;
      if (size > limitMB * 1024 * 1024) {
        req.destroy();
        reject(new Error("Body too large"));
      }
      chunks.push(chunk);
    });
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

function readJSONBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", chunk => chunks.push(chunk));
    req.on("end", () => {
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString()));
      } catch (e) {
        reject(e);
      }
    });
    req.on("error", reject);
  });
}

// ─── GLOBAL HEADERS ─────────────────────────────────────────────────────────
app.use((req, res, next) => {
  res.setHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  res.setHeader("X-Content-Hash", crypto.createHash("sha256").update(Date.now().toString()).digest("hex").slice(0,16));
  next();
});

// ─── UPLOAD ─────────────────────────────────────────────────────────────────
app.post("/upload", async (req, res) => {
  const fileId   = req.headers["x-file-id"];
  const idx      = parseInt(req.headers["x-chunk-index"], 10);
  const hash     = req.headers["x-hash"];
  const size     = parseInt(req.headers["x-size"] || "0", 10);

  if (!fileId || isNaN(idx) || !hash)
    return res.status(400).json({ error: "Missing required headers" });

  const dir = path.join(UPLOAD_DIR, fileId);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  const manifest = readManifest(fileId) || {
    fileId, receivedChunks: {}, status: "in_progress",
    createdAt: new Date().toISOString()
  };

  const raw = await readBody(req);

  // Hash the raw payload bytes
  const actual = crypto.createHash("sha256").update(raw).digest("hex");
  if (actual !== hash)
    return res.status(415).json({ error: "Hash mismatch", expected: hash, actual });

  const chunkPath = path.join(dir, String(idx).padStart(8, "0"));
  fs.writeFileSync(chunkPath, raw);          // store raw — no COIL header

  manifest.receivedChunks[idx] = {
    hash, size: raw.length,
    receivedAt: new Date().toISOString()
  };
  manifest.status = "in_progress";
  manifest.updatedAt = new Date().toISOString();
  writeManifest(fileId, manifest);

  return res.json({ ok: true, chunkIndex: idx, hashVerified: true });
});

// ─── RETRIEVE RECONSTRUCTED FILE ────────────────────────────────────────────

app.get("/data/:fileId", (req, res) => {
  const { fileId } = req.params;
  // fileId from URL may include extension — check as-is first, then by known extensions
  const candidates = [
    path.join(UPLOAD_DIR, fileId),           // /data/abc.bin → uploads/abc.bin
    path.join(UPLOAD_DIR, `${fileId}.bin`), // no-ext → with .bin
    path.join(UPLOAD_DIR, `${fileId}.json`),
    path.join(DATA_DIR, fileId),
    path.join(DATA_DIR, `${fileId}.bin`),
    path.join(DATA_DIR, `${fileId}.json`),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) {
      const data = fs.readFileSync(p);
      res.setHeader("Content-Length", data.length);
      res.setHeader("Content-Type", p.endsWith(".json") ? "application/json" : "application/octet-stream");
      res.setHeader("Cache-Control", "no-store");
      res.setHeader("Pragma", "no-cache");
      res.setHeader("X-Content-Hash", crypto.createHash("sha256").update(data).digest("hex"));
      return res.status(200).send(data);
    }
  }
  return res.status(404).json({ error: "Not found" });
});

// ─── DELTA STATUS ───────────────────────────────────────────────────────────

app.get("/status/:fileId", (req, res) => {
  const manifest = readManifest(req.params.fileId);
  if (!manifest) return res.json({ fileId: req.params.fileId, status: "not_found", receivedChunks: [] });
  const indices = Object.keys(manifest.receivedChunks).map(Number).sort((a, b) => a - b);
  return res.json({
    fileId: req.params.fileId, status: manifest.status,
    receivedChunks: indices, totalReceived: indices.length,
    createdAt: manifest.createdAt, updatedAt: manifest.updatedAt
  });
});

app.get("/status", (req, res) => {
  const { fileId } = req.query;
  const manifest = readManifest(fileId);
  if (!manifest) return res.json({});
  const map = {};
  // Use manifest indices (unpadded) for consistency with client lookups
  for (const [idx, info] of Object.entries(manifest.receivedChunks)) {
    map[idx] = info.hash;  // idx is already "0", "1", ... (string keys from JSON)
  }
  res.json(map);
});

// ─── COMPLETE + RECONSTRUCT ────────────────────────────────────────────────

app.post("/complete", async (req, res) => {
  const fileId = req.headers["x-file-id"];
  const body = await readJSONBody(req);
  const { originalExt = "bin", totalExpected } = body || {};

  if (!fileId) return res.status(400).json({ error: "Missing x-file-id header" });

  const manifest = readManifest(fileId);
  if (!manifest) return res.status(404).json({ error: "No upload found" });
  const indices = Object.keys(manifest.receivedChunks).map(Number).sort((a, b) => a - b);
  if (indices.length === 0) return res.status(400).json({ error: "No chunks received" });

  // Red Line: encrypted uploads — skip reassembly, seal manifest
  // The server stores ciphertext only. Client holds the key and decrypts locally.
  console.log("[COMPLETE] manifest.encrypted =", manifest.encrypted, typeof manifest.encrypted);
  if (manifest.encrypted) {
    manifest.status = "complete";
    manifest.updatedAt = new Date().toISOString();
    writeManifest(fileId, manifest);
    return res.json({
      ok: true,
      path: `encrypted:${fileId}/${indices.length}:ciphertext-only:server:cannot:decrypt`,
      chunksReconstructed: indices.length,
      encrypted: true,
      note: "Server holds ciphertext only. Decryption requires client-side key."
    });
  }

  // Plaintext reassembly — FLAT storage: raw slices only
  const buffers = [];
  for (const idx of indices) {
    const chunkPath = path.join(UPLOAD_DIR, fileId, String(idx).padStart(8, "0"));
    buffers.push(fs.readFileSync(chunkPath));
  }
  const assembled = Buffer.concat(buffers);

  // ── Verification before write ──────────────────────────────────────
  const { expectedSize, expectedHash } = body || {};
  if (expectedSize != null && assembled.length !== expectedSize)
    return res.status(422).json({
      error: "Size mismatch", expected: expectedSize, actual: assembled.length
    });
  if (expectedHash) {
    const actualHash = crypto.createHash("sha256").update(assembled).digest("hex");
    if (actualHash !== expectedHash)
      return res.status(422).json({
        error: "Hash mismatch", expected: expectedHash, actual: actualHash
      });
    console.log(`[COMPLETE] ✓ verified ${assembled.length} bytes SHA256=${actualHash}`);
  }

  const isJSON = originalExt === "json";
  const outputPath = path.join(isJSON ? DATA_DIR : UPLOAD_DIR, `${fileId}.${originalExt}`);
  fs.writeFileSync(outputPath, assembled);

  manifest.status = "complete";
  manifest.updatedAt = new Date().toISOString();
  writeManifest(fileId, manifest);

  return res.json({ ok: true, path: outputPath, chunksReconstructed: indices.length });
});

// ─── JSON PATCH APPLY (+DIFF) ────────────────────────────────────────────────

app.post("/diff", async (req, res) => {
  const body = await readJSONBody(req);
  const { fileId, baseVersion, newVersion, ops } = body;

  if (!fileId || !ops) {
    return res.status(400).json({ error: "fileId and ops are required" });
  }

  console.log(`[DIFF] fileId=${fileId} baseVersion=${baseVersion} newVersion=${newVersion} ops=${JSON.stringify(ops)}`);

  const filePath = path.join(DATA_DIR, `${fileId}.json`);
  let current = {};
  if (fs.existsSync(filePath)) {
    try { current = JSON.parse(fs.readFileSync(filePath, "utf8")); } catch {}
  }
  console.log(`[DIFF] current before patch: ${JSON.stringify(current)}`);

  const updated = applyPatch(current, ops);
  console.log(`[DIFF] updated after patch: ${JSON.stringify(updated)}`);

  fs.writeFileSync(filePath, JSON.stringify(updated, null, 2));

  // Save patch to audit trail
  const patchFile = path.join(PATCHES_DIR, `${fileId}_v${baseVersion}_to_v${newVersion}.json`);
  fs.writeFileSync(patchFile, JSON.stringify({ fileId, baseVersion, newVersion, ops, appliedAt: new Date().toISOString() }, null, 2));

  return res.json({ status: "patched", version: newVersion });
});

// ─── DELETE CHUNK (vandal test / repair) ────────────────────────────────────

app.delete("/chunks/:fileId/:chunkIndex", async (req, res) => {
  const { fileId, chunkIndex } = req.params;
  const dir = path.join(UPLOAD_DIR, fileId);
  const chunkPath = path.join(dir, String(chunkIndex).padStart(8, "0"));
  if (!fs.existsSync(chunkPath)) return res.status(404).json({ error: "Chunk not found" });
  fs.unlinkSync(chunkPath);

  const manifest = readManifest(fileId);
  if (!manifest) return res.status(404).json({ error: "No upload found" });
  delete manifest.receivedChunks[chunkIndex];
  manifest.updatedAt = new Date().toISOString();
  writeManifest(fileId, manifest);

  return res.json({ ok: true, chunkIndex });
});

// ─── AGGREGATE STATUS (for live UI polling) ─────────────────────────────────

app.get("/tasks", (req, res) => {
  const manifestsDir = MANIFESTS_DIR;
  if (!fs.existsSync(manifestsDir)) return res.json({ tasks: [], summary: { total: 0, complete: 0, in_progress: 0 } });

  const files = fs.readdirSync(manifestsDir).filter(f => f.endsWith(".json"));
  const tasks = files.map(name => {
    const manifest = JSON.parse(fs.readFileSync(path.join(manifestsDir, name), "utf8"));
    const totalChunks = Object.keys(manifest.receivedChunks || {}).length;
    return {
      fileId: manifest.fileId,
      status: manifest.status,
      totalReceived: totalChunks,
      createdAt: manifest.createdAt,
      updatedAt: manifest.updatedAt,
    };
  });

  const summary = {
    total: tasks.length,
    complete: tasks.filter(t => t.status === "complete").length,
    in_progress: tasks.filter(t => t.status === "in_progress").length,
    totalChunks: tasks.reduce((sum, t) => sum + t.totalReceived, 0),
  };

  res.json({ tasks, summary, serverUptime: process.uptime() });
});

// ─── SERVER ─────────────────────────────────────────────────────────────────

app.get("/health", (req, res) => {
  res.json({ status: "ok", uptime: process.uptime() });
});

app.listen(PORT, () => {
  console.log(`[COIL] Server running on port ${PORT}`);
  console.log(`[COIL] Upload dir: ${UPLOAD_DIR}`);
  console.log(`[COIL] Manifests: ${MANIFESTS_DIR}`);
  console.log(`[COIL] Data: ${DATA_DIR}`);
  console.log(`[COIL] Patches: ${PATCHES_DIR}`);
});

module.exports = app;
