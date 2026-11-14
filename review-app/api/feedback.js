import { deny, sendJson, isAuthorized } from "../lib/auth.js";
import { getMerged } from "../lib/logic.js";

export default async function handler(req, res) {
  if (req.method !== "GET") {
    res.statusCode = 405;
    res.end("method not allowed");
    return;
  }
  if (!(await isAuthorized(req))) return deny(req, res);
  try {
    const data = await getMerged();
    sendJson(req, res, 200, data);
  } catch (err) {
    sendJson(req, res, 500, { error: "store failed" });
  }
}
