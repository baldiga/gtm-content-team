// timeline pages: pause every animation at t seconds (all CSS animations share one start time)
window.__tkSeek = (t) => {
  for (const a of document.getAnimations()) { a.pause(); a.currentTime = t * 1000; }
  for (const fn of (window.__tkSeekHooks || [])) fn(t);
};
(async () => {
  const rep = { fit: [], outside: [], unsafe: [], hooks: [] };
  try { await document.fonts.ready; } catch (e) {}
  const W = innerWidth, H = innerHeight, story = document.documentElement.classList.contains("f-story");
  // 1) shrink-to-fit: zoom .fit>.in until it fits its box (min 0.6)
  for (const box of document.querySelectorAll(".fit")) {
    const inner = box.firstElementChild; if (!inner) continue;
    let z = 1; inner.style.zoom = 1;
    if (box.dataset.zoom) {   // fixed zoom (shared across the frames of one story/carousel)
      z = parseFloat(box.dataset.zoom); inner.style.zoom = z;
      const o = box.scrollHeight > box.clientHeight + 1 || box.scrollWidth > box.clientWidth + 1;
      rep.fit.push({ id: box.dataset.id || box.className, zoom: z, overflow: o, fixed: true }); continue;
    }
    const cards = box.querySelectorAll(".ob,.wn,.blk,.node,.stg,.gb,.qt,td,th");
    const over = () => box.scrollHeight > box.clientHeight + 1 || box.scrollWidth > box.clientWidth + 1 || inner.getBoundingClientRect().height > box.clientHeight + 1
      || [...cards].some((el) => el.scrollWidth > el.clientWidth + 1);
    while (over() && z > 0.6) { z = Math.round((z - 0.02) * 100) / 100; inner.style.zoom = z; }
    // grow short content to fill the space (cap data-max, default 1.45), keep 6% air
    if (box.classList.contains("grow") && z === 1) {
      const max = parseFloat(box.dataset.max || (story ? "1.9" : "1.6"));
      const tight = () => over() || inner.getBoundingClientRect().height > box.clientHeight * 0.94;
      while (z < max) { const nz = Math.round((z + 0.02) * 100) / 100; inner.style.zoom = nz; if (tight()) { inner.style.zoom = z; break; } z = nz; }
    }
    rep.fit.push({ id: box.dataset.id || box.className, zoom: z, overflow: over() });
  }
  if (window.__tkTimeline) window.__tkSeek(window.__tkTimeline.check_at || 0);   // measure at the full state
  // 2) template hooks (connectors, annotations) after layout is final
  for (const fn of (window.__tkHooks || [])) { try { fn(); rep.hooks.push("ok"); } catch (e) { rep.hooks.push(String(e)); } }
  // timeline pages are checked at their full state
  if (window.__tkTimeline) window.__tkSeek(window.__tkTimeline.check_at || 0);
  // 3) bounds: every visible text run inside the canvas; stories inside the IG safe zone
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = tw.nextNode())) {
    const t = n.textContent.replace(/[\u200e\u200f\s]/g, "");
    if (!t) continue;
    const el = n.parentElement; const cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || parseFloat(cs.opacity) === 0 || el.closest("[data-hidden]")) continue;
    const r = document.createRange(); r.selectNodeContents(n);
    for (const b of r.getClientRects()) {
      if (b.width < 1) continue;
      if (b.left < -1 || b.right > W + 1 || b.top < -1 || b.bottom > H + 1) rep.outside.push(t.slice(0, 40));
      if (story && (b.top < 250 || b.bottom > H - 340)) rep.unsafe.push(t.slice(0, 40) + " @" + Math.round(b.top));
    }
  }
  window.__tkReport = rep; window.__tkDone = true;
})();
