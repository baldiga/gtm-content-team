import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { commonHeaders, isSessionAuthorized } from "../lib/auth.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "public");

export default async function handler(req, res) {
  commonHeaders(res);
  const ok = await isSessionAuthorized(req);
  const name = ok ? "index.html" : "login.html";
  const html = readFileSync(join(ROOT, name), "utf8");
  res.statusCode = 200;
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.end(html);
}
