/**
 * Build task queue + drain via uploadPool
 *
 * Usage:
 *   let tasks = [];
 *   for (let i = 0; i < chunks.length; i++) {
 *     const chunk = chunks[i];
 *     const hash = await computeHash(chunk);
 *     tasks.push(async () => {
 *       const compressed = await compressChunk(chunk);
 *       await uploadWithRetry(compressed, i, hash, fileId);
 *     });
 *   }
 *   await uploadPool(tasks);
 */
