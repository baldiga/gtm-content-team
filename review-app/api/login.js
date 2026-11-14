import { clientIp, commonHeaders, loginCookie, passwordMatches, readBody, sendJson } from "../lib/auth.js";
import { sessionFromRequest } from "../lib/session.js";
import { checkLoginAllowed, recordLoginFailure, recordLoginSuccess } from "../lib/ratelimit.js";

export default async function handler(req, res) {
  commonHeaders(res);
  if (req.method === "GET") {
    const ok = await sessionFromRequest(req);
    sendJson(req, res, 200, { ok: Boolean(ok) });
    return;
  }
  if (req.method !== "POST") {
    res.statusCode = 405;
    res.end("method not allowed");
    return;
  }
  const ip = clientIp(req);
  try {
    const gate = await checkLoginAllowed(ip);
    if (!gate.allowed) {
      res.setHeader("Retry-After", String(gate.retryAfter || 60));
      sendJson(req, res, 429, { error: "ניסיתם יותר מדי פעמים. נסו שוב בעוד כמה דקות." });
      return;
    }
    const body = await readBody(req);
    const password = body?.password;
    if (await passwordMatches(password)) {
      await recordLoginSuccess(ip);
      const cookie = await loginCookie();
      sendJson(req, res, 200, { ok: true }, cookie);
      return;
    }
    const fail = await recordLoginFailure(ip, gate);
    if (fail.locked) {
      res.setHeader("Retry-After", String(fail.retryAfter || 60));
      sendJson(req, res, 429, { error: "ניסיתם יותר מדי פעמים. נסו שוב בעוד כמה דקות." });
      return;
    }
    sendJson(req, res, 401, { error: "הסיסמה לא נכונה." });
  } catch (err) {
    sendJson(req, res, 500, { error: "הכניסה נכשלה, נסו שוב." });
  }
}
