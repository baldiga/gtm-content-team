import { get, put } from "@vercel/blob";
import { sha256hex } from "./auth.js";

const PATHNAME = `${process.env.BLOB_PREFIX || "content-review"}/login-guard.json`;
const MAX_FAILS = 5;
const LOCK_MS = 15 * 60 * 1000;

async function loadGuard() {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) return {};
  try {
    const result = await get(PATHNAME, { access: "private", token, useCache: false });
    if (!result || result.statusCode !== 200 || !result.stream) return {};
    return JSON.parse(await new Response(result.stream).text());
  } catch {
    return {};
  }
}

async function saveGuard(data) {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) return;
  await put(PATHNAME, JSON.stringify(data) + "\n", {
    access: "private",
    addRandomSuffix: false,
    allowOverwrite: true,
    contentType: "application/json; charset=utf-8",
    token,
  });
}

export async function checkLoginAllowed(ip) {
  const key = await sha256hex(ip || "unknown");
  const data = await loadGuard();
  const rec = data[key];
  if (rec?.lockedUntil && Date.now() < rec.lockedUntil) {
    const retryAfter = Math.ceil((rec.lockedUntil - Date.now()) / 1000);
    return { allowed: false, retryAfter };
  }
  return { allowed: true, data, key };
}

export async function recordLoginFailure(ip, prior) {
  const data = prior?.data || (await loadGuard());
  const key = prior?.key || (await sha256hex(ip || "unknown"));
  const rec = data[key] || { fails: 0 };
  if (rec.lockedUntil && Date.now() >= rec.lockedUntil) {
    rec.fails = 0;
    rec.lockedUntil = 0;
  }
  rec.fails = (rec.fails || 0) + 1;
  if (rec.fails >= MAX_FAILS) {
    rec.lockedUntil = Date.now() + LOCK_MS;
    rec.fails = 0;
  }
  data[key] = rec;
  await saveGuard(data);
  if (rec.lockedUntil && Date.now() < rec.lockedUntil) {
    return { locked: true, retryAfter: Math.ceil((rec.lockedUntil - Date.now()) / 1000) };
  }
  return { locked: false };
}

export async function recordLoginSuccess(ip) {
  const data = await loadGuard();
  const key = await sha256hex(ip || "unknown");
  if (data[key]) {
    delete data[key];
    await saveGuard(data);
  }
}
