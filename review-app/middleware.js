import { verifySessionValue, parseCookies, safeEqual } from "./lib/session.js";

const PUBLIC_PATHS = new Set([
  "/login",
  "/login.html",
  "/api/login",
  "/styles.css",
  "/robots.txt",
]);

function isPublic(pathname) {
  if (PUBLIC_PATHS.has(pathname)) return true;
  if (pathname.startsWith("/fonts/")) return true;
  if (pathname.startsWith("/demo/")) return true;
  return false;
}

function teamAuthorized(request) {
  const team = process.env.TEAM_API_KEY || "";
  if (!team) return false;
  const header = request.headers.get("x-team-key") || request.headers.get("x-access-key") || "";
  if (safeEqual(header, team)) return true;
  const auth = request.headers.get("authorization") || "";
  if (auth.toLowerCase().startsWith("bearer ")) {
    return safeEqual(auth.slice(7).trim(), team);
  }
  return false;
}

export const config = {
  matcher: ["/((?!_next/|favicon.ico).*)"],
};

export default async function middleware(request) {
  const url = new URL(request.url);
  const { pathname } = url;
  if (isPublic(pathname)) return;
  if (pathname.startsWith("/api/") && teamAuthorized(request)) return;

  const cookies = parseCookies(request.headers.get("cookie"));
  const ok = await verifySessionValue(cookies.review_session);
  if (ok) return;

  if (pathname.startsWith("/api/")) {
    return new Response(JSON.stringify({ error: "unauthorized" }), {
      status: 401,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "x-robots-tag": "noindex, nofollow",
        "cache-control": "no-store",
      },
    });
  }
  return Response.redirect(new URL("/login", url), 302);
}
