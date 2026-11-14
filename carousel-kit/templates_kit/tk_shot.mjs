#!/usr/bin/env node
// Batch screenshot through a running Chrome DevTools port.
// Waits for window.__tkDone (fit + connector hooks + bounds check), then
// captures and prints one "REPORT <json>" line per job.
// Usage: node tk_shot.mjs PORT JOBS.json   (JOBS = [{uri,out,w,h}, ...])
import fs from "node:fs";
const [port, jobsPath] = process.argv.slice(2);
const jobs = JSON.parse(fs.readFileSync(jobsPath, "utf8"));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function newTarget() {
  const res = await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" });
  if (!res.ok) throw new Error(`json/new -> ${res.status}`);
  return res.json();
}
function cdp(ws) {
  let id = 0; const pending = new Map(); const listeners = [];
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id); pending.delete(msg.id);
      msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
    } else if (msg.method) for (const fn of listeners) fn(msg);
  };
  return {
    send(method, params = {}) {
      const i = ++id;
      return new Promise((resolve, reject) => { pending.set(i, { resolve, reject }); ws.send(JSON.stringify({ id: i, method, params })); });
    },
    once(method, timeout = 15000) {
      return new Promise((resolve, reject) => {
        const t = setTimeout(() => reject(new Error(`timeout ${method}`)), timeout);
        listeners.push((m) => { if (m.method === method) { clearTimeout(t); resolve(m.params); } });
      });
    },
  };
}
const target = await newTarget();
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error("ws error")); });
const s = cdp(ws);
await s.send("Page.enable"); await s.send("Runtime.enable");
let failed = 0;
for (const job of jobs) {
  try {
    await s.send("Emulation.setDeviceMetricsOverride", { width: job.w, height: job.h, deviceScaleFactor: 1, mobile: false, screenWidth: job.w, screenHeight: job.h });
    const loaded = s.once("Page.loadEventFired");
    await s.send("Page.navigate", { url: job.uri });
    await loaded;
    let done = false;
    for (let i = 0; i < 100 && !done; i++) {
      const r = await s.send("Runtime.evaluate", { expression: "!!window.__tkDone", returnByValue: true });
      done = r.result.value; if (!done) await sleep(50);
    }
    const rep = await s.send("Runtime.evaluate", { expression: "JSON.stringify(window.__tkReport||{})", returnByValue: true });
    await sleep(60);
    const clip = { x: 0, y: 0, width: job.w, height: job.h, scale: 1 };
    if (job.times) {
      // timeline page: seek every CSS animation to t, wait two frames, capture
      for (let i = 0; i < job.times.length; i++) {
        await s.send("Runtime.evaluate", { expression: `window.__tkSeek(${job.times[i]}); new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`, awaitPromise: true });
        const fr = await s.send("Page.captureScreenshot", { format: "png", fromSurface: true, captureBeyondViewport: false, clip });
        fs.writeFileSync(job.outs[i], Buffer.from(fr.data, "base64"));
      }
    } else {
      const shot = await s.send("Page.captureScreenshot", { format: "png", fromSurface: true, captureBeyondViewport: false, clip });
      fs.writeFileSync(job.out, Buffer.from(shot.data, "base64"));
    }
    console.log("REPORT " + JSON.stringify({ out: job.out, done, report: JSON.parse(rep.result.value || "{}") }));
  } catch (e) { failed++; console.error(`FAIL ${job.out}: ${e.message}`); }
}
await fetch(`http://127.0.0.1:${port}/json/close/${target.id}`).catch(() => {});
ws.close();
process.exit(failed ? 1 : 0);
