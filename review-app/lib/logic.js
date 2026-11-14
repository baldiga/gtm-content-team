import { randomBytes } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadState, saveState, nowIso } from "./store.js";

const OWNER_ID = process.env.OWNER_ID || "owner";
const OWNER_LABEL = process.env.OWNER_LABEL || "את/ה";
const TEAM_LABEL = process.env.TEAM_LABEL || "הצוות";
const TIMEZONE = process.env.TIMEZONE || "Asia/Jerusalem";

const STATUS_HE = {
  pending: "ממתין לאישור",
  changes: "ביקשת שינויים",
  approved: "מאושר",
  archived: "הוסר מהשבוע",
};

const ARCHIVE_REASONS = {
  cut: "נגזר",
  "idea-bank": "עבר לבנק רעיונות",
};

const catalog = JSON.parse(
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), "catalog.json"), "utf8")
);

export function getCatalog() {
  return catalog;
}

export function catalogCodes() {
  return (catalog.pieces || []).map((p) => p.code);
}

export function merge(state) {
  const out = [];
  for (const piece of catalog.pieces || []) {
    const overlay = (state.pieces || {})[piece.code] || {};
    const merged = { ...piece };
    const status = overlay.status || "pending";
    merged.status = status;
    merged.status_he = overlay.status_he || STATUS_HE[status] || status;
    merged.version = overlay.version || piece.version || "v1";
    if (overlay.body != null) {
      merged.body = overlay.body;
      merged.chars = String(overlay.body).length;
    }
    if (overlay.first_comment != null) merged.first_comment = overlay.first_comment;
    if (overlay.images != null) {
      merged.images = overlay.images;
      merged.image_pending = overlay.images.length === 0;
    }
    merged.comments = overlay.comments || [];
    if (overlay.archive_reason) {
      merged.archive_reason = overlay.archive_reason;
      merged.archive_reason_he = overlay.archive_reason_he || ARCHIVE_REASONS[overlay.archive_reason] || overlay.archive_reason;
    }
    out.push(merged);
  }
  return {
    title: catalog.title,
    week: catalog.week,
    week_label: catalog.week_label,
    updated: state.updated || catalog.updated,
    timezone: TIMEZONE,
    owner_id: OWNER_ID,
    owner_label: OWNER_LABEL,
    pieces: out,
  };
}

function pieceBucket(state, code) {
  state.pieces = state.pieces || {};
  state.pieces[code] = state.pieces[code] || {};
  return state.pieces[code];
}

export function addComment(state, code, author, text, typ, version) {
  const piece = pieceBucket(state, code);
  const cat = (catalog.pieces || []).find((p) => p.code === code) || {};
  const ver = version || piece.version || cat.version || "v1";
  const comments = Array.isArray(piece.comments) ? piece.comments.slice() : [];
  comments.push({
    id: randomBytes(6).toString("hex"),
    at: nowIso(),
    author,
    author_he: author === OWNER_ID ? OWNER_LABEL : TEAM_LABEL,
    text,
    type: typ,
    version: ver,
  });
  piece.comments = comments;
}

export function setStatus(state, code, status) {
  const piece = pieceBucket(state, code);
  piece.status = status;
  piece.status_he = STATUS_HE[status];
}

export async function getMerged() {
  return merge(await loadState());
}

export async function handleAction(body) {
  const typ = body?.type;
  const code = body?.code;
  const text = String(body?.text || "").trim();
  const codes = catalogCodes();
  const state = await loadState();

  if (typ === "approve_all") {
    for (const c of codes) {
      const current = (state.pieces || {})[c]?.status;
      if (current !== "approved" && current !== "archived") {
        setStatus(state, c, "approved");
        addComment(state, c, OWNER_ID, "אושר הכל", "approve", state.pieces[c]?.version);
      }
    }
    await saveState(state);
    return { ok: true, data: merge(state) };
  }

  if (!codes.includes(code)) return { ok: false, status: 400, error: "unknown piece" };
  if ((state.pieces || {})[code]?.status === "archived") {
    return { ok: false, status: 400, error: "archived piece" };
  }

  if (typ === "comment") {
    if (!text) return { ok: false, status: 400, error: "empty comment" };
    addComment(state, code, OWNER_ID, text, "comment");
  } else if (typ === "approve") {
    setStatus(state, code, "approved");
    addComment(state, code, OWNER_ID, text || "אושר", "approve");
  } else if (typ === "changes") {
    if (!text) return { ok: false, status: 400, error: "empty comment" };
    setStatus(state, code, "changes");
    addComment(state, code, OWNER_ID, text, "request_changes");
  } else {
    return { ok: false, status: 400, error: "unknown action" };
  }

  await saveState(state);
  return { ok: true, data: merge(state) };
}

export async function handleTeam(body) {
  const action = body?.action;
  const state = await loadState();

  if (action === "reset") {
    // Used only to wipe test data after a live check. Leaves comments/status empty.
    state.pieces = {};
    await saveState(state);
    return { ok: true, data: merge(state) };
  }

  const code = body?.code;
  const codes = catalogCodes();
  if (!codes.includes(code)) return { ok: false, status: 400, error: "unknown piece" };
  const piece = pieceBucket(state, code);

  if (action === "reply") {
    const text = String(body?.text || "").trim();
    if (!text) return { ok: false, status: 400, error: "empty comment" };
    addComment(state, code, "team", text, "reply", body.version || piece.version);
  } else if (action === "version") {
    const version = String(body?.version || "").trim();
    if (!version) return { ok: false, status: 400, error: "missing version" };
    piece.version = version;
    if (body.body != null) piece.body = body.body;
    if (body.first_comment != null) piece.first_comment = body.first_comment;
    if (body.images != null) {
      piece.images = body.images;
      piece.image_pending = body.images.length === 0;
    }
    const note = String(body.note || body.text || `עודכן ל${version}`).trim();
    if (piece.status !== "approved" && piece.status !== "archived") setStatus(state, code, "pending");
    addComment(state, code, "team", note, "version", version);
  } else if (action === "images") {
    if (!Array.isArray(body.images)) return { ok: false, status: 400, error: "images must be a list" };
    let existing = Array.isArray(piece.images) ? piece.images.slice() : [];
    if (!existing.length) {
      const cat = (catalog.pieces || []).find((p) => p.code === code) || {};
      existing = Array.isArray(cat.images) ? cat.images.slice() : [];
    }
    piece.images = (body.mode || "replace") === "append" ? existing.concat(body.images) : body.images;
    piece.image_pending = piece.images.length === 0;
    const note = String(body.note || body.text || "עודכנו תמונות").trim();
    addComment(state, code, "team", note, "images", piece.version);
    if (piece.status !== "approved" && piece.status !== "archived") setStatus(state, code, "pending");
  } else if (action === "body") {
    if (body.body == null) return { ok: false, status: 400, error: "missing body" };
    piece.body = body.body;
    if (body.first_comment != null) piece.first_comment = body.first_comment;
    if (body.version) piece.version = body.version;
    addComment(state, code, "team", body.note || body.text || "עודכן הטקסט", "version", piece.version);
    if (piece.status !== "approved" && piece.status !== "archived") setStatus(state, code, "pending");
  } else if (action === "archive") {
    const reason = String(body.reason || "").trim();
    if (!ARCHIVE_REASONS[reason]) return { ok: false, status: 400, error: "reason must be cut or idea-bank" };
    setStatus(state, code, "archived");
    piece.archive_reason = reason;
    piece.archive_reason_he = ARCHIVE_REASONS[reason];
    const fallback = reason === "idea-bank" ? "הועבר לבנק רעיונות" : "הוסר מהשבוע (נגזר)";
    const note = String(body.note || body.text || fallback).trim();
    addComment(state, code, "team", note, "archive", piece.version);
  } else {
    return { ok: false, status: 400, error: "unknown action" };
  }

  await saveState(state);
  return { ok: true, data: merge(state) };
}
