const COOKIE = "review_session";
const MAX_AGE = 30 * 24 * 60 * 60; // 30 days

function getSecret() {
  return process.env.SESSION_SECRET || "";
}

function toHex(buffer) {
  return [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function hmacHex(secret, message) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message));
  return toHex(sig);
}

function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i += 1) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

export function parseCookies(header) {
  const out = {};
  for (const part of String(header || "").split(";")) {
    const idx = part.indexOf("=");
    if (idx === -1) continue;
    const k = part.slice(0, idx).trim();
    const v = part.slice(idx + 1).trim();
    out[k] = decodeURIComponent(v);
  }
  return out;
}

export async function createSessionValue() {
  const secret = getSecret();
  if (!secret) throw new Error("SESSION_SECRET is missing");
  const exp = Math.floor(Date.now() / 1000) + MAX_AGE;
  const payload = `v1.${exp}`;
  const sig = await hmacHex(secret, payload);
  return `${payload}.${sig}`;
}

export async function verifySessionValue(value) {
  const secret = getSecret();
  if (!secret || !value) return false;
  const parts = String(value).split(".");
  if (parts.length !== 3 || parts[0] !== "v1") return false;
  const [ver, expRaw, sig] = parts;
  const exp = Number(expRaw);
  if (!Number.isFinite(exp) || exp * 1000 < Date.now()) return false;
  const expected = await hmacHex(secret, `${ver}.${expRaw}`);
  return safeEqual(sig, expected);
}

export async function sessionFromRequest(req) {
  const cookies = parseCookies(req.headers?.cookie || req.headers?.get?.("cookie"));
  return verifySessionValue(cookies[COOKIE]);
}

export function sessionCookieHeader(value) {
  return [
    `${COOKIE}=${encodeURIComponent(value)}`,
    "Path=/",
    "HttpOnly",
    "Secure",
    "SameSite=Strict",
    `Max-Age=${MAX_AGE}`,
  ].join("; ");
}

export { COOKIE, MAX_AGE, safeEqual };
