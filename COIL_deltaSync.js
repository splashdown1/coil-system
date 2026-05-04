/**
 * getServerChunkMap — fetch server's known chunks for a given fileId
 * Used for delta sync: compare local hashes vs server hashes before uploading
 */
async function getServerChunkMap(fileId) {
  const res = await fetch(`http://localhost:3000/status?fileId=${fileId}`);
  if (!res.ok) throw new Error(`Server returned ${res.status}`);
  return res.json(); // { index: hash }
}
