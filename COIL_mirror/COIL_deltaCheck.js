/**
 * Delta sync check — skip chunk if server already has identical hash
 * Call this inside the upload loop, before uploading:
 *
 *   for (let i = 0; i < totalChunks; i++) {
 *     const serverMap = await getServerChunkMap(fileId);
 *     const hash = await computeHash(chunkData);
 *     if (serverMap[i] === hash) {
 *       log(`Chunk ${i} ⏭ identical (delta skip)`);
 *       continue;
 *     }
 *     await uploadChunk(chunkData, i, hash, fileId);
 *   }
 */
async function deltaCheck(chunkData, fileId, chunkIndex) {
  const serverMap = await getServerChunkMap(fileId);
  const hash = await computeHash(chunkData);
  if (serverMap[chunkIndex] === hash) {
    return { skipped: true, hash };
  }
  return { skipped: false, hash };
}
