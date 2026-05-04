/**
 * encryptChunk — AES-GCM-256 encrypt a chunk before upload
 * Returns { encrypted: ArrayBuffer, iv: Uint8Array, exportedKey: ArrayBuffer }
 *
 * NOTE: The key must be stored or shared with the server to decrypt on the other side.
 * For now, keys are NOT exported — add key export + storage if you need E2E encryption.
 *
 * Usage:
 *   const { encrypted, iv } = await encryptChunk(chunk);
 *   // send encrypted + iv to server
 */
async function encryptChunk(chunk) {
  const key = await crypto.subtle.generateKey(
    { name: "AES-GCM", length: 256 },
    true,
    ["encrypt"]
  );
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const data = await chunk.arrayBuffer();
  const encrypted = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    data
  );
  return { encrypted, iv };
}
