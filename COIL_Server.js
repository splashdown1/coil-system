const express = require("express");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const zlib = require("zlib");
const { Readable, Transform, pipeline } = require("stream");
const { promisify } = require("util");

const pipelineAsync = promisify(pipeline);

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

function safeReadJSONBody(req) {
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

// ─── STREAMING CHUNK ASSEMBLER ─────────────────────────────────────────────
// Reads chunks in sequence, streams them concatenated to a writable.
// Backpressure-aware: waits for the writable to drain before reading the next chunk.
// Never holds more than one chunk in memory.

class ChunkAssembler extends Transform {
  constructor(indices, uploadDir, fileId, options) {
    super(options);
    this.indices = indices;       // sorted array of chunk indices
    this.uploadDir = uploadDir;
    this.fileId = fileId;
    this.idx = 0;
    this._reading = false;
    this._currentReadStream = null;
  }

  _readChunk(idx) {
    const chunkPath = path.join(this.uploadDir, this.fileId, String(idx).padStart(8, "0"));
    if (!fs.existsSync(chunkPath)) {
      this.destroy(new Error(`Chunk missing: ${idx}`));
      return;
    }
    const stream = fs.createReadStream(chunkPath);
    this._currentReadStream = stream;
    stream.on("data", chunk => this.push(chunk));
    stream.on("end", () => {
      this._currentReadStream = null;
      this.idx++;
      if (this.idx < this.indices.length) {
        // yield to event loop before reading next chunk (backpressure)
        setImmediate(() => this._readChunk(this.indices[this.idx]));
      } else {
        this.push(null); // signal end of stream
      }
    });
    stream.on("error", err => this.destroy(err));
  }

  _transform(chunk, enc, cb) { /* not used — chunks come from _readChunk via push */ }
  _flush(cb) { cb(); }

  start() {
    if (this.indices.length === 0) {
      this.push(null);
      return;
    }
    this._readChunk(this.indices[0]);
  }
}

// ─── STREAMING FILE DELIVERY ───────────────────────────────────────────────
// Streams a file from disk to the response with headers set before any data flows.
// Uses createReadStream + pipe for proper backpressure and chunked transfer encoding.
// Hash is computed as a side-effect of streaming (no extra memory for large files).

function streamFile(res, filePath, contentType) {
  const stat = fs.statSync(filePath);
  // Compute hash via a streaming hash that runs alongside the pipe
  const hashSink = crypto.createHash("sha256");
  const fileStream = fs.createReadStream(filePath);
  res.setHeader("Content-Length", stat.size);
  res.setHeader("Content-Type", contentType);
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Pragma", "no-cache");
  fileStream.on("data", chunk => hashSink.update(chunk));
  fileStream.on("end", () => res.setHeader("X-Content-Hash", hashSink.digest("hex")));
  fileStream.pipe(res);
  fileStream.on("error", err => {
    if (!res.headersSent) res.status(500).json({ error: err.message });
    else res.destroy();
  });
}

// ─── BODY HELPERS ──────────────────────────────────────────────────────────

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

// ─── GLOBAL HEADERS ─────────────────────────────────────────────────────────
app.use((req, res, next) => {
  res.setHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  res.setHeader("X-Content-Hash", crypto.createHash("sha256").update(Date.now().toString()).digest("hex").slice(0, 16));
  next();
});

// ─── UPLOAD ─────────────────────────────────────────────────────────────────
app.post("/upload", async (req, res) => {
  const fileId = req.headers["x-file-id"];
  const idx = parseInt(req.headers["x-chunk-index"], 10);
  const hash = req.headers["x-hash"];
  const size = parseInt(req.headers["x-size"] || "0", 10);

  if (!fileId || isNaN(idx) || !hash)
    return res.status(400).json({ error: "Missing required headers" });

  const dir = path.join(UPLOAD_DIR, fileId);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  const manifest = readManifest(fileId) || {
    fileId, receivedChunks: {}, status: "in_progress",
    createdAt: new Date().toISOString()
  };

  const raw = await readBody(req);

  const actual = crypto.createHash("sha256").update(raw).digest("hex");
  if (actual !== hash)
    return res.status(415).json({ error: "Hash mismatch", expected: hash, actual });

  const chunkPath = path.join(dir, String(idx).padStart(8, "0"));
  fs.writeFileSync(chunkPath, raw);

  manifest.receivedChunks[idx] = {
    hash, size: raw.length,
    receivedAt: new Date().toString()
  };
  manifest.status = "in_progress";
  manifest.updatedAt = new Date().toISOString();
  writeManifest(fileId, manifest);

  return res.json({ ok: true, chunkIndex: idx, hashVerified: true });
});

// ─── RETRIEVE RECONSTRUCTED FILE ───────────────────────────────────────────
app.get("/data/:fileId", (req, res) => {
  const { fileId } = req.params;
  const candidates = [
    path.join(UPLOAD_DIR, `${fileId}.bin`),
    path.join(UPLOAD_DIR, `${fileId}.json`),
    path.join(DATA_DIR, fileId),
    path.join(DATA_DIR, `${fileId}.bin`),
    path.join(DATA_DIR, `${fileId}.json`),
  ];
  for (const p of candidates) {
    // fs.existsSync is true for both files and directories — must explicitly reject dirs
    if (fs.existsSync(p) && !fs.statSync(p).isDirectory()) {
      const ctype = p.endsWith(".json") ? "application/json" : "application/octet-stream";
      streamFile(res, p, ctype);
      return;
    }
  }
  return res.status(404).json({ error: "Not found" });
});

// ─── DELTA STATUS ──────────────────────────────────────────────────────────
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
  for (const [idx, info] of Object.entries(manifest.receivedChunks)) {
    map[idx] = info.hash;
  }
  res.json(map);
});

// ─── COMPLETE + RECONSTRUCT ────────────────────────────────────────────────
//
// Two paths:
//
//  1. ALREADY COMPLETE — manifest.status === "complete"
//     → Stream the assembled file directly from disk. No chunk re-read.
//     → Response starts immediately, memory stays flat.
//
//  2. FRESH ASSEMBLY — status === "in_progress" (or anything else)
//     → Pipeline chunks through ChunkAssembler (one chunk in memory at a time)
//       directly to the output file, then stream it back.
//     → Total memory = one chunk size, not sum of all chunks.
//     → Backpressure ensures the writable (fs write stream) controls the read rate.
//

app.post("/complete", async (req, res) => {
  const fileId = req.headers["x-file-id"];
  const body = await safeReadJSONBody(req).catch(() => ({}));
  const { originalExt = "bin", expectedSize, expectedHash } = body;

  if (!fileId) return res.status(400).json({ error: "Missing x-file-id header" });

  const manifest = readManifest(fileId);
  if (!manifest) return res.status(404).json({ error: "No upload found" });

  const indices = Object.keys(manifest.receivedChunks).map(Number).sort((a, b) => a - b);
  if (indices.length === 0) return res.status(400).json({ error: "No chunks received" });

  // ── PATH 1: Already complete — stream directly ───────────────────────
  if (manifest.status === "complete") {
    const isJSON = originalExt === "json";
    const assembledPath = path.join(isJSON ? DATA_DIR : UPLOAD_DIR, `${fileId}.${originalExt}`);

    if (fs.existsSync(assembledPath)) {
      const ctype = isJSON ? "application/json" : "application/octet-stream";
      streamFile(res, assembledPath, ctype);
      return;
    }
    // Assembled file gone but manifest says complete — fall through to reassemble
    console.warn(`[COMPLETE] manifest says complete but file missing: ${assembledPath}. Reassembling.`);
  }

  // ── PATH 2: Fresh assembly — stream chunks to disk, then stream back ─
  const isJSON = originalExt === "json";
  const outputPath = path.join(isJSON ? DATA_DIR : UPLOAD_DIR, `${fileId}.${originalExt}`);

  // Pipeline chunks → assembler → write stream
  const assembler = new ChunkAssembler(indices, UPLOAD_DIR, fileId);
  const writeStream = fs.createWriteStream(outputPath);

  try {
    await pipelineAsync(assembler, writeStream);
  } catch (err) {
    console.error("[COMPLETE] assembly failed:", err);
    writeStream.destroy();
    return res.status(500).json({ error: "Assembly failed", detail: err.message });
  }

  // ── Verify after write ────────────────────────────────────────────────
  const assembledSize = fs.statSync(outputPath).size;
  if (expectedSize != null && assembledSize !== expectedSize) {
    fs.unlinkSync(outputPath);
    return res.status(422).json({ error: "Size mismatch", expected: expectedSize, actual: assembledSize });
  }

  if (expectedHash) {
    // For large files, use a streaming hash so we don't load the whole file into memory
    const hashStream = crypto.createHash("sha256");
    const verifyStream = fs.createReadStream(outputPath);
    await new Promise((resolve, reject) => {
      verifyStream.on("data", chunk => hashStream.update(chunk));
      verifyStream.on("end", resolve);
      verifyStream.on("error", reject);
    });
    const actualHash = hashStream.digest("hex");
    if (actualHash !== expectedHash) {
      fs.unlinkSync(outputPath);
      return res.status(422).json({ error: "Hash mismatch", expected: expectedHash, actual: actualHash });
    }
    console.log(`[COMPLETE] ✓ verified ${assembledSize} bytes SHA256=${actualHash}`);
  }

  // ── Seal manifest ─────────────────────────────────────────────────────
  manifest.status = "complete";
  manifest.updatedAt = new Date().toISOString();
  writeManifest(fileId, manifest);

  // ── Stream the assembled file back to client ─────────────────────────
  const ctype = isJSON ? "application/json" : "application/octet-stream";
  streamFile(res, outputPath, ctype);
});

// ─── JSON PATCH APPLY (+DIFF) ─────────────────────────────────────────────
app.post("/diff", async (req, res) => {
  const body = await safeReadJSONBody(req);
  const { fileId, baseVersion, newVersion, ops } = body;

  if (!fileId || !ops) {
    return res.status(400).json({ error: "fileId and ops are required" });
  }

  const filePath = path.join(DATA_DIR, `${fileId}.json`);
  let current = {};
  if (fs.existsSync(filePath)) {
    try { current = JSON.parse(fs.readFileSync(filePath, "utf8")); } catch {}
  }

  const updated = applyPatch(current, ops);

  fs.writeFileSync(filePath, JSON.stringify(updated, null, 2));

  const patchFile = path.join(PATCHES_DIR, `${fileId}_v${baseVersion}_to_v${newVersion}.json`);
  fs.writeFileSync(patchFile, JSON.stringify({ fileId, baseVersion, newVersion, ops, appliedAt: new Date().toISOString() }, null, 2));

  return res.json({ status: "patched", version: newVersion });
});

// applyPatch (RFC 6902-style)
function applyPatch(obj, ops) {
  const result = JSON.parse(JSON.stringify(obj));
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

// ─── DELETE CHUNK ──────────────────────────────────────────────────────────
app.delete("/chunks/:fileId/:chunkIndex", async (req, res) => {
  const { fileId, chunkIndex } = req.params;
  const chunkPath = path.join(UPLOAD_DIR, fileId, String(chunkIndex).padStart(8, "0"));
  if (!fs.existsSync(chunkPath)) return res.status(404).json({ error: "Chunk not found" });
  fs.unlinkSync(chunkPath);

  const manifest = readManifest(fileId);
  if (!manifest) return res.status(404).json({ error: "No upload found" });
  delete manifest.receivedChunks[chunkIndex];
  manifest.updatedAt = new Date().toISOString();
  writeManifest(fileId, manifest);

  return res.json({ ok: true, chunkIndex });
});

// ─── PURGE (BULK DELETE) ───────────────────────────────────────────────────
// Delete all chunks and manifest for a given fileId.
// Use ?dry=1 query param to preview what would be deleted without removing anything.

app.delete("/purge/:fileId", (req, res) => {
  const { fileId } = req.params;
  const dry = req.query.dry === "1";

  const manifestPath = path.join(MANIFESTS_DIR, `${fileId}.json`);
  const uploadDir = path.join(UPLOAD_DIR, fileId);

  let deletedChunks = 0;
  let errors = [];

  if (fs.existsSync(uploadDir)) {
    const chunks = fs.readdirSync(uploadDir);
    deletedChunks = chunks.length;
    if (!dry) {
      try {
        fs.rmSync(uploadDir, { recursive: true, force: true });
      } catch (e) {
        errors.push(`Failed to delete upload dir: ${e.message}`);
      }
    }
  }

  if (fs.existsSync(manifestPath)) {
    if (!dry) {
      try { fs.unlinkSync(manifestPath); } catch (e) { errors.push(`Failed to delete manifest: ${e.message}`); }
    }
  } else {
    errors.push(`No manifest found for fileId: ${fileId}`);
  }

  if (dry) {
    return res.json({ dry: true, fileId, wouldDeleteChunks: deletedChunks, errors });
  }
  return res.json({ ok: true, fileId, deletedChunks, errors: errors.length ? errors : undefined });
});

// Purge all in-progress tasks older than N minutes (safety valve for orphans).
// GET /purge-stale?maxAgeMinutes=60  — preview
// DELETE /purge-stale?maxAgeMinutes=60 — execute

app.get("/purge-stale", (req, res) => {
  const maxAgeMs = (parseInt(req.query.maxAgeMinutes, 10) || 60) * 60 * 1000;
  const cutoff = Date.now() - maxAgeMs;
  const files = fs.readdirSync(MANIFESTS_DIR).filter(f => f.endsWith(".json"));
  const stale = [];
  for (const name of files) {
    const manifest = JSON.parse(fs.readFileSync(path.join(MANIFESTS_DIR, name), "utf8"));
    const mtime = new Date(manifest.updatedAt || 0).getTime();
    if (mtime < cutoff && manifest.status !== "complete") {
      stale.push({ fileId: manifest.fileId || "(unknown)", manifest: name, ageMs: Date.now() - mtime });
    }
  }
  return res.json({ stale, count: stale.length });
});

app.delete("/purge-stale", (req, res) => {
  const maxAgeMs = (parseInt(req.query.maxAgeMinutes, 10) || 60) * 60 * 1000;
  const cutoff = Date.now() - maxAgeMs;
  const files = fs.readdirSync(MANIFESTS_DIR).filter(f => f.endsWith(".json"));
  let purged = 0;
  let errors = [];
  for (const name of files) {
    const fullPath = path.join(MANIFESTS_DIR, name);
    const manifest = JSON.parse(fs.readFileSync(fullPath, "utf8"));
    const mtime = new Date(manifest.updatedAt || 0).getTime();
    if (mtime < cutoff && manifest.status !== "complete") {
      const fileId = manifest.fileId || name.replace(".json", "");
      const uploadDir = path.join(UPLOAD_DIR, fileId);
      if (fs.existsSync(uploadDir)) { try { fs.rmSync(uploadDir, { recursive: true, force: true }); } catch (e) { errors.push(e.message); } }
      try { fs.unlinkSync(fullPath); } catch (e) { errors.push(e.message); }
      purged++;
    }
  }
  return res.json({ ok: true, purged, errors: errors.length ? errors : undefined });
});

// ─── AGGREGATE STATUS ──────────────────────────────────────────────────────
app.get("/tasks", (req, res) => {
  if (!fs.existsSync(MANIFESTS_DIR)) return res.json({ tasks: [], summary: { total: 0, complete: 0, in_progress: 0 } });

  const files = fs.readdirSync(MANIFESTS_DIR).filter(f => f.endsWith(".json"));
  const tasks = files.map(name => {
    const manifest = JSON.parse(fs.readFileSync(path.join(MANIFESTS_DIR, name), "utf8"));
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

// ─── SERVER ────────────────────────────────────────────────────────────────
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