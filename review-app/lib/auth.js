import { sessionFromRequest, createSessionValue, sessionCookieHeader, safeEqual } from "./session.js";

export async function sha256hex(value) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(String(value)));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function isTeamToken(token) {
  const team = process.env.TEAM_API_KEY || "";
  return safeEqual(token, team);
}

export function teamTokenFromRequest(req) {
  const header = req.headers["x-team-key"] || req.headers["x-access-key"];
  if (header) return String(header);
  const auth = req.headers.authorization || "";
  if (auth.toLowerCase().startsWith("bearer ")) return auth.slice(7).trim();
  return "";
}

export async function isSessionAuthorized(req) {
  return sessionFromRequest(req);
}

export async function isAuthorized(req) {
  if (isTeamToken(teamTokenFromRequest(req))) return true;
  return isSessionAuthorized(req);
}

export function commonHeaders(res) {
  res.setHeader("X-Robots-Tag", "noindex, nofollow");
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("Referrer-Policy", "no-referrer");
  res.setHeader("Cache-Control", "no-store");
}

export function deny(req, res) {
  commonHeaders(res);
  res.statusCode = 401;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.end(JSON.stringify({ error: "unauthorized" }));
}

export function sendJson(req, res, status, payload, setCookie) {
  commonHeaders(res);
  if (setCookie) res.setHeader("Set-Cookie", setCookie);
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.end(JSON.stringify(payload));
}

export async function passwordMatches(password) {
  const expected = process.env.ACCESS_KEY_SHA256 || "";
  if (!expected || password == null) return false;
  const got = await sha256hex(password);
  return safeEqual(got, expected);
}

export async function loginCookie() {
  const value = await createSessionValue();
  return sessionCookieHeader(value);
}

export function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      const raw = Buffer.concat(chunks).toString("utf8");
      if (!raw) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch (err) {
        reject(err);
      }
    });
    req.on("error", reject);
  });
}

export function clientIp(req) {
  const fwd = req.headers["x-forwarded-for"];
  if (fwd) return String(fwd).split(",")[0].trim();
  return req.headers["x-real-ip"] || req.socket?.remoteAddress || "unknown";
}
