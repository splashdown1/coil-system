/**
 * uploadPool — Concurrency-limited task runner for parallel chunk uploads
 * Limits to CONCURRENCY concurrent tasks; queues the rest
 *
 * Usage:
 *   const tasks = chunks.map((chunk, i) => () => uploadWithRetry(chunk, i, hash, fileId));
 *   await uploadPool(tasks); // max 4 concurrent uploads at a time
 */
const CONCURRENCY = 4;

async function uploadPool(tasks) {
  let i = 0;
  async function worker() {
    while (i < tasks.length) {
      const task = tasks[i++];
      await task();
    }
  }
  await Promise.all(Array(CONCURRENCY).fill().map(worker));
}
