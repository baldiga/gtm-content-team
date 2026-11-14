import { get, put } from "@vercel/blob";

const PATHNAME = `${process.env.BLOB_PREFIX || "content-review"}/state.json`;

function emptyState() {
  return { updated: new Date().toISOString(), pieces: {} };
}

export async function loadState() {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) return emptyState();
  try {
    const result = await get(PATHNAME, { access: "private", token, useCache: false });
    if (!result || result.statusCode !== 200 || !result.stream) return emptyState();
    const data = JSON.parse(await new Response(result.stream).text());
    data.pieces = data.pieces || {};
    return data;
  } catch {
    return emptyState();
  }
}

export async function saveState(state) {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) {
    throw new Error("BLOB_READ_WRITE_TOKEN is missing");
  }
  state.updated = nowIso();
  await put(PATHNAME, JSON.stringify(state, null, 2) + "\n", {
    access: "private",
    addRandomSuffix: false,
    allowOverwrite: true,
    contentType: "application/json; charset=utf-8",
    token,
  });
  return state;
}

export function nowIso() {
  const now = new Date();
  const fmt = new Intl.DateTimeFormat("en-GB", {
    timeZone: process.env.TIMEZONE || "Asia/Jerusalem",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  });
  const parts = Object.fromEntries(fmt.formatToParts(now).map((p) => [p.type, p.value]));
  const tzPart = new Intl.DateTimeFormat("en-US", {
    timeZone: process.env.TIMEZONE || "Asia/Jerusalem",
    timeZoneName: "longOffset",
  })
    .formatToParts(now)
    .find((p) => p.type === "timeZoneName");
  const m = /GMT([+-])(\d+)(?::(\d+))?/.exec(tzPart?.value || "GMT+2");
  const sign = m ? m[1] : "+";
  const hh = String(m ? m[2] : 2).padStart(2, "0");
  const mm = String(m && m[3] ? m[3] : 0).padStart(2, "0");
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}:${parts.second}${sign}${hh}:${mm}`;
}
