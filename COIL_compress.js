/**
 * compressChunk — gzip compress a Uint8Array or ArrayBuffer using CompressionStream Web API
 * Returns a compressed ArrayBuffer ready for fetch
 *
 * Usage:
 *   const compressed = await compressChunk(chunkData); // Uint8Array
 *   const compressed = await compressChunk(await file.arrayBuffer()); // ArrayBuffer
 */
async function compressChunk(data) {
  if (data instanceof ArrayBuffer) {
    data = new Uint8Array(data);
  } else if (data instanceof Uint8Array) {
    // already fine
  } else {
    throw new Error("Unsupported data type — pass ArrayBuffer or Uint8Array");
  }

  const cs = new CompressionStream("gzip");
  const writer = cs.writable.getWriter();
  writer.write(data);
  writer.close();

  const reader = cs.readable.getReader();
  const chunks = [];
  let totalSize = 0;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    totalSize += value.byteLength;
  }

  // Merge all chunks into a single Uint8Array
  const result = new Uint8Array(totalSize);
  let offset = 0;
  for (const chunk of chunks) {
    result.set(new Uint8Array(chunk), offset);
    offset += chunk.byteLength;
  }

  return result.buffer; // ArrayBuffer
}
