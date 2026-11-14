#!/usr/bin/env node
// Capture one HTML file through an already-running Chrome DevTools port.
// Usage: node cdp_screenshot.mjs PORT FILE_URI OUT_PNG WIDTH HEIGHT

const [port, uri, outPath, widthArg, heightArg] = process.argv.slice(2);
const width = Number(widthArg || 1080);
const height = Number(heightArg || 1350);

if (!port || !uri || !outPath) {
  console.error("usage: node cdp_screenshot.mjs PORT FILE_URI OUT_PNG WIDTH HEIGHT");
  process.exit(2);
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

async function openTarget(port, url) {
  // Prefer /json/new so we don't reuse someone else's tab.
  const res = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`, {
    method: "PUT",
  });
  if (res.ok) return res.json();
  const version = await getJson(`http://127.0.0.1:${port}/json/version`);
  // Fall back: just use the first page.
  const list = await getJson(`http://127.0.0.1:${port}/json/list`);
  const page = list.find((t) => t.type === "page") || list[0];
  if (!page) throw new Error(`no targets: ${JSON.stringify(version)}`);
  return page;
}

function cdp(ws) {
  let id = 0;
  const pending = new Map();
  const listeners = [];
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(JSON.stringify(msg.error)));
      else resolve(msg.result);
    } else if (msg.method) {
      for (const fn of listeners) fn(msg);
    }
  };
  return {
    send(method, params = {}) {
      const thisId = ++id;
      return new Promise((resolve, reject) => {
        pending.set(thisId, { resolve, reject });
        ws.send(JSON.stringify({ id: thisId, method, params }));
      });
    },
    on(fn) {
      listeners.push(fn);
    },
  };
}

function waitEvent(session, method, timeoutMs = 10000) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error(`timeout waiting for ${method}`)), timeoutMs);
    session.on((msg) => {
      if (msg.method === method) {
        clearTimeout(t);
        resolve(msg.params);
      }
    });
  });
}

const target = await openTarget(port, "about:blank");
const wsUrl = target.webSocketDebuggerUrl;
if (!wsUrl) throw new Error(`no websocket for target ${JSON.stringify(target)}`);

const ws = new WebSocket(wsUrl);
await new Promise((resolve, reject) => {
  ws.onopen = resolve;
  ws.onerror = (e) => reject(new Error(`websocket error: ${e}`));
});

const session = cdp(ws);
await session.send("Page.enable");
await session.send("Runtime.enable");
await session.send("Emulation.setDeviceMetricsOverride", {
  width,
  height,
  deviceScaleFactor: 1,
  mobile: false,
  screenWidth: width,
  screenHeight: height,
});

const loaded = waitEvent(session, "Page.loadEventFired", 15000);
await session.send("Page.navigate", { url: uri });
await loaded;
// Fonts are local; give the compositor a brief tick.
await session.send("Page.bringToFront").catch(() => {});
await sleep(150);
await session.send("Runtime.evaluate", {
  expression: "document.fonts ? document.fonts.ready : Promise.resolve()",
  awaitPromise: true,
}).catch(() => {});
await sleep(50);

const shot = await session.send("Page.captureScreenshot", {
  format: "png",
  fromSurface: true,
  captureBeyondViewport: false,
  clip: { x: 0, y: 0, width, height, scale: 1 },
});
if (!shot || !shot.data) throw new Error("empty screenshot");

const fs = await import("node:fs");
fs.writeFileSync(outPath, Buffer.from(shot.data, "base64"));

// Close the tab we opened if possible.
if (target.id) {
  await fetch(`http://127.0.0.1:${port}/json/close/${target.id}`).catch(() => {});
}
ws.close();
console.log(`wrote ${outPath}`);
