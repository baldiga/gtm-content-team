import { deny, sendJson, isAuthorized, readBody } from "../lib/auth.js";
import { handleAction } from "../lib/logic.js";

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.statusCode = 405;
    res.end("method not allowed");
    return;
  }
  if (!(await isAuthorized(req))) return deny(req, res);
  try {
    const body = await readBody(req);
    const result = await handleAction(body);
    if (!result.ok) return sendJson(req, res, result.status, { error: result.error });
    sendJson(req, res, 200, result.data);
  } catch (err) {
    sendJson(req, res, 500, { error: "store failed" });
  }
}
