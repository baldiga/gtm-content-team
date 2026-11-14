export class AuthError extends Error {
  constructor() {
    super("unauthorized");
    this.name = "AuthError";
  }
}

async function parse(res) {
  if (res.status === 401 || res.status === 403) throw new AuthError();
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || "request failed");
    err.status = res.status;
    throw err;
  }
  return data;
}

function apiUrl(base, path) {
  const root = base.startsWith("http") ? base : window.location.origin + base;
  const full = new URL(path.replace(/^\//, ""), root.endsWith("/") ? root : root + "/");
  return full.toString();
}

export function createLocalStore(config) {
  const base = config.apiBase || "/api";

  async function getState() {
    const res = await fetch(apiUrl(base, "state"), {
      credentials: "include",
      cache: "no-store",
    });
    return parse(res);
  }

  async function postAction(body) {
    const res = await fetch(apiUrl(base, "action"), {
      method: "POST",
      credentials: "include",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return parse(res);
  }

  return {
    getState,
    comment: (code, text) => postAction({ type: "comment", code, text }),
    approve: (code) => postAction({ type: "approve", code }),
    approveAll: () => postAction({ type: "approve_all" }),
    requestChanges: (code, text) => postAction({ type: "changes", code, text }),
  };
}
