import { createLocalStore, AuthError } from "./stores/local.js";

const STATUS_HE = {
  pending: "ממתין לאישור",
  changes: "ביקשת שינויים",
  approved: "מאושר",
  archived: "הוסר מהשבוע",
};

const ARCHIVE_REASON_HE = {
  cut: "נגזר",
  "idea-bank": "עבר לבנק רעיונות",
};

const root = document.getElementById("app");
let store;
let state = null;
let filterPlatform = "all";
let filterDay = "all";
let toastTimer;

function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatWhen(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return new Intl.DateTimeFormat("he-IL", {
    timeZone: "Asia/Jerusalem",
    day: "numeric",
    month: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

function showToast(text, kind = "ok") {
  document.querySelector(".toast")?.remove();
  const n = el(`<div class="toast ${escapeHtml(kind)}" role="status">${escapeHtml(text)}</div>`);
  document.body.appendChild(n);
  clearTimeout(toastTimer);
  if (kind === "wait") return;
  const ms = kind === "err" ? 4500 : 3500;
  toastTimer = setTimeout(() => n.remove(), ms);
}

function versionNumber(value) {
  const m = String(value || "v1").match(/(\d+)/);
  return m ? Number(m[1]) : 0;
}

function versionLabel(p) {
  const raw = String(p?.version || "v1").trim() || "v1";
  return /^v/i.test(raw) ? raw : `v${raw}`;
}

function hasNewerVersion(p) {
  const current = versionNumber(p.version);
  const ownerId = state.owner_id || "owner";
  const ownerNotes = (p.comments || []).filter((c) => c.author === ownerId);
  if (!ownerNotes.length || !current) return false;
  return current > versionNumber(ownerNotes[ownerNotes.length - 1].version || "v1");
}

function renderVersionTag(p) {
  const fresh = hasNewerVersion(p);
  return `<span class="ver-wrap"><span class="ver-tag">${escapeHtml(versionLabel(p))}</span>${fresh ? `<span class="ver-new">חדש</span>` : ""}</span>`;
}

function syncSendEnabled(scope) {
  const origin = scope || root;
  const cards = origin.matches?.(".card") ? [origin] : [...origin.querySelectorAll(".card")];
  cards.forEach((card) => {
    const ta = card.querySelector("textarea");
    const send = card.querySelector('[data-act="changes"]');
    if (!send || send.dataset.busy === "1") return;
    send.disabled = !(ta?.value || "").trim();
  });
}

function goLogin() {
  location.href = "/login";
}

function isArchived(p) {
  return p?.status === "archived";
}

function lineupPieces() {
  return (state.pieces || []).filter((p) => !isArchived(p));
}

function archivedPieces() {
  return (state.pieces || []).filter((p) => isArchived(p));
}

function archiveReasonHe(p) {
  return p.archive_reason_he || ARCHIVE_REASON_HE[p.archive_reason] || STATUS_HE.archived;
}

function counts() {
  const pieces = lineupPieces();
  return {
    all: pieces.length,
    approved: pieces.filter((p) => p.status === "approved").length,
    changes: pieces.filter((p) => p.status === "changes").length,
    pending: pieces.filter((p) => p.status === "pending").length,
    archived: archivedPieces().length,
  };
}

function visiblePieces() {
  return lineupPieces().filter((p) => {
    if (filterPlatform !== "all" && p.platform !== filterPlatform) return false;
    if (filterDay !== "all" && p.day !== filterDay) return false;
    return true;
  });
}

function groupByDay(pieces) {
  const groups = [];
  for (const p of pieces) {
    const last = groups[groups.length - 1];
    if (!last || last.day !== p.day) {
      groups.push({ day: p.day, label: `${p.day_he} · ${p.date_he}`, pieces: [p] });
    } else {
      last.pieces.push(p);
    }
  }
  return groups;
}

function renderGallery(images, kindClass) {
  if (!images.length) return "";
  const isStory = kindClass === "story";
  return `
    <div class="gallery-wrap">
      <div class="gallery-label">${isStory ? "סטוריז" : images[0].kind === "slide" ? "שקפי הקרוסלה" : "תמונות"}</div>
      <div class="gallery" data-kind="${escapeHtml(kindClass)}">
        ${images
          .map(
            (img, i) => `
          <button type="button" class="slide ${isStory ? "story" : ""}" data-open="${escapeHtml(img.id)}" aria-label="${escapeHtml(img.label)}">
            <img src="${escapeHtml(img.src)}" alt="${escapeHtml(img.label)}" width="${img.width || ""}" height="${img.height || ""}" loading="lazy"${img.fallback ? ` data-fallback="${escapeHtml(img.fallback)}"` : ""} />
          </button>`
          )
          .join("")}
      </div>
      <div class="pager">${images[0].label}${images.length > 1 ? ` · 1 מתוך ${images.length}` : ""}</div>
    </div>`;
}


function firstCommentLabel(p) {
  return p.platform === "x" ? "ריפליי ראשון" : "תגובה ראשונה";
}

function renderFirstComment(p) {
  if (!p.first_comment) return "";
  return `<div class="first-comment ${p.platform === "x" ? "as-reply" : ""}">
      <div class="fc-head"><span>${firstCommentLabel(p)}</span><button type="button" class="copy-btn" data-copy="${escapeHtml(p.code)}">העתק</button></div>
      <div class="fc-text">${escapeHtml(p.first_comment)}</div>
    </div>`;
}

function renderCopy(p, charLine, over) {
  const posts = Array.isArray(p.posts) && p.posts.length ? p.posts : null;
  if (posts) {
    const items = posts
      .map((post) => {
        const n = post.n || "";
        const of = post.of || posts.length;
        const chars = post.chars != null ? post.chars : String(post.text || "").length;
        const limit = p.char_limit;
        const postOver = limit && chars > limit;
        const line = limit ? `${chars} / ${limit} תווים` : `${chars} תווים`;
        return `<div class="x-post">
            <div class="x-post-n">פוסט ${escapeHtml(String(n))}/${escapeHtml(String(of))}</div>
            <pre class="body">${escapeHtml(post.text)}</pre>
            <p class="chars${postOver ? " over" : ""}">${escapeHtml(line)}</p>
          </div>`;
      })
      .join("");
    return `<div class="x-thread">${items}${renderFirstComment(p)}</div>`;
  }
  return `<pre class="body">${escapeHtml(p.body)}</pre>
      <p class="chars${over ? " over" : ""}">${escapeHtml(charLine)}</p>
      ${renderFirstComment(p)}`;
}

function archivedCard(p) {
  return `
    <article class="card archived-card" id="piece-${escapeHtml(p.code)}" data-code="${escapeHtml(p.code)}">
      <div class="card-top">
        <span class="code">${escapeHtml(p.code)}</span>
        <span class="sub">${escapeHtml(p.platform_he)} · ${escapeHtml(p.day_he)} ${escapeHtml(p.date_he)}</span>
        <span class="card-flags">${renderVersionTag(p)}<span class="status archived">${escapeHtml(archiveReasonHe(p))}</span></span>
      </div>
      <h2>${escapeHtml(p.title)}</h2>
    </article>`;
}

function pieceCard(p) {
  const slides = (p.images || []).filter((i) => i.kind === "slide" || i.kind === "feed" || i.kind === "image");
  const stories = (p.images || []).filter((i) => i.kind === "story");
  const charLine = p.char_limit ? `${p.chars} / ${p.char_limit} תווים` : `${p.chars} תווים`;
  const over = p.char_limit && p.chars > p.char_limit;
  const comments = p.comments || [];
  return `
    <article class="card" id="piece-${escapeHtml(p.code)}" data-code="${escapeHtml(p.code)}">
      <div class="card-top">
        <span class="code">${escapeHtml(p.code)}</span>
        <span class="sub">${escapeHtml(p.platform_he)} · ${escapeHtml(p.account)}</span>
        <span class="card-flags">${renderVersionTag(p)}<span class="status ${escapeHtml(p.status)}">${escapeHtml(p.status_he || STATUS_HE[p.status] || p.status)}</span></span>
      </div>
      <h2>${escapeHtml(p.title)}</h2>
      <div class="sub piece-meta">${escapeHtml(p.day_he)} ${escapeHtml(p.date_he)}</div>
      ${
        p.image_pending || !(p.images || []).length
          ? `<div class="missing">עדיין אין תמונה. הצוות מעלה בקרוב.</div>`
          : `${renderGallery(slides, slides.some((i) => i.kind === "slide") ? "slide" : "feed")}${renderGallery(stories, "story")}`
      }
      ${renderCopy(p, charLine, over)}
      <div class="thread">
        <h3>הערות</h3>
        ${
          comments.length
            ? comments
                .map(
                  (c) => `<div class="note ${escapeHtml(c.author)}">
                    <div class="who">${escapeHtml(c.author_he)} · ${escapeHtml(formatWhen(c.at))}${c.version ? ` · ${escapeHtml(c.version)}` : ""}</div>
                    <div>${escapeHtml(c.text)}</div>
                  </div>`
                )
                .join("")
            : `<p class="sub">עדיין אין הערות על הפוסט הזה.</p>`
        }
      </div>
      <div class="composer">
        <textarea placeholder="כתבו מה צריך לשנות…" data-comment="${escapeHtml(p.code)}"></textarea>
        <div class="actions">
          <button type="button" class="btn changes" data-act="changes" data-code="${escapeHtml(p.code)}" disabled>שלח שינויים</button>
          <button type="button" class="btn approve" data-act="approve" data-code="${escapeHtml(p.code)}">אשר</button>
        </div>
      </div>
    </article>`;
}

function render() {
  const scrollY = window.scrollY;
  const c = counts();
  const days = [...new Map(lineupPieces().map((p) => [p.day, p.day_he])).entries()];
  const visible = visiblePieces();
  const groups = groupByDay(visible);
  const archived = archivedPieces();
  root.innerHTML = `
    <header class="top">
      <h1>${escapeHtml(state.title || "תוכן לאישור")}</h1>
      <p class="meta">${escapeHtml(state.week_label || "")}${state.updated ? ` · עודכן ${escapeHtml(formatWhen(state.updated))}` : ""}</p>
      <div class="counts">
        <span class="chip">${c.all} פוסטים</span>
        <span class="chip wait">${c.pending} ממתינים</span>
        <span class="chip edit">${c.changes} לתיקון</span>
        <span class="chip ok">${c.approved} מאושרים</span>
      </div>
    </header>
    <div class="filters" role="tablist" aria-label="פלטפורמה">
      <button type="button" class="filter-btn${filterPlatform === "all" ? " active" : ""}" data-platform="all">הכל</button>
      <button type="button" class="filter-btn${filterPlatform === "linkedin" ? " active" : ""}" data-platform="linkedin">LinkedIn</button>
      <button type="button" class="filter-btn${filterPlatform === "instagram" ? " active" : ""}" data-platform="instagram">Instagram</button>
      <button type="button" class="filter-btn${filterPlatform === "x" ? " active" : ""}" data-platform="x">X</button>
    </div>
    <div class="filters" role="tablist" aria-label="יום">
      <button type="button" class="filter-btn${filterDay === "all" ? " active" : ""}" data-day="all">כל הימים</button>
      ${days
        .map(
          ([day, he]) =>
            `<button type="button" class="filter-btn${filterDay === day ? " active" : ""}" data-day="${escapeHtml(day)}">${escapeHtml(he)}</button>`
        )
        .join("")}
    </div>
    <button type="button" class="approve-all">מאשר הכל</button>
    <main class="list">
      ${
        groups.length
          ? groups
              .map((g) => `<h2 class="day-head">${escapeHtml(g.label)}</h2>${g.pieces.map(pieceCard).join("")}`)
              .join("")
          : `<p class="empty-filter">אין פוסטים בסינון הזה.</p>`
      }
    </main>
    ${
      archived.length
        ? `<details class="archived-fold">
        <summary>הוסר מהשבוע · ${archived.length} פוסטים</summary>
        ${archived.map(archivedCard).join("")}
      </details>`
        : ""
    }
  `;

  root.querySelectorAll("[data-platform]").forEach((btn) =>
    btn.addEventListener("click", () => {
      filterPlatform = btn.dataset.platform;
      render();
    })
  );
  root.querySelectorAll("[data-day]").forEach((btn) =>
    btn.addEventListener("click", () => {
      filterDay = btn.dataset.day;
      render();
    })
  );
  root.querySelector(".approve-all")?.addEventListener("click", confirmApproveAll);
  root.querySelectorAll("[data-act]").forEach((btn) => btn.addEventListener("click", onAction));
  root.querySelectorAll("[data-copy]").forEach((btn) => btn.addEventListener("click", onCopy));
  root.querySelectorAll("[data-open]").forEach((btn) => btn.addEventListener("click", onOpenImage));
  root.querySelectorAll("textarea[data-comment]").forEach((ta) =>
    ta.addEventListener("input", () => syncSendEnabled(ta.closest(".card")))
  );
  root.querySelectorAll(".gallery").forEach(bindPager);
  bindFallbackImages(root);
  syncSendEnabled(root);
  window.scrollTo(0, scrollY);
}

function bindPager(gallery) {
  const pager = gallery.parentElement.querySelector(".pager");
  const slides = [...gallery.querySelectorAll(".slide")];
  if (!pager || slides.length < 2) return;
  const update = () => {
    const left = gallery.scrollLeft;
    let best = 0;
    let bestDist = Infinity;
    slides.forEach((s, i) => {
      const dist = Math.abs(s.offsetLeft - left);
      if (dist < bestDist) {
        bestDist = dist;
        best = i;
      }
    });
    const img = state.pieces.flatMap((p) => p.images || []).find((x) => x.id === slides[best].dataset.open);
    pager.textContent = `${img?.label || slides[best].getAttribute("aria-label")} · ${best + 1} מתוך ${slides.length}`;
  };
  gallery.addEventListener("scroll", update, { passive: true });
}

function pieceByCode(code) {
  return (state.pieces || []).find((p) => p.code === code);
}

async function onCopy(ev) {
  const code = ev.currentTarget.dataset.copy;
  const piece = pieceByCode(code);
  if (!piece?.first_comment) return;
  try {
    await navigator.clipboard.writeText(piece.first_comment);
    ev.currentTarget.textContent = "הועתק";
    showToast("התגובה הועתקה");
    setTimeout(() => {
      ev.currentTarget.textContent = "העתק";
    }, 1600);
  } catch {
    showToast("לא הצלחתי להעתיק, העתיקו ידנית");
  }
}

function allImagesOf(piece) {
  return (piece.images || []).filter((i) => i.kind !== "video" && i.kind !== "pdf");
}

function bindFallbackImages(scope) {
  (scope || document).querySelectorAll("img[data-fallback]").forEach((img) => {
    img.addEventListener("error", () => {
      const fb = img.getAttribute("data-fallback");
      if (!fb) return;
      img.removeAttribute("data-fallback");
      img.src = fb;
    });
  });
}

function onOpenImage(ev) {
  const id = ev.currentTarget.dataset.open;
  const piece = ev.currentTarget.closest("[data-code]");
  const code = piece?.dataset.code;
  const p = pieceByCode(code);
  if (!p) return;
  const images = allImagesOf(p);
  const start = Math.max(0, images.findIndex((i) => i.id === id));
  openLightbox(images, start, p);
}

function openLightbox(images, start, piece) {
  document.querySelector(".lightbox")?.remove();
  const box = el(`
    <div class="lightbox" role="dialog" aria-modal="true">
      <div class="lightbox-bar">
        <button type="button" data-close>סגירה</button>
        <span class="lb-label"></span>
        ${piece ? renderVersionTag(piece) : "<span></span>"}
      </div>
      <div class="lightbox-track">
        ${images
          .map(
            (img) => `<figure><img src="${escapeHtml(img.src || img.original)}" alt="${escapeHtml(img.label)}"${img.fallback ? ` data-fallback="${escapeHtml(img.fallback)}"` : ""} /></figure>`
          )
          .join("")}
      </div>
    </div>`);
  const track = box.querySelector(".lightbox-track");
  const label = box.querySelector(".lb-label");
  const update = () => {
    const w = track.clientWidth || 1;
    const i = Math.round(track.scrollLeft / w);
    const img = images[Math.min(Math.max(i, 0), images.length - 1)];
    label.textContent = `${img.label} · ${Math.min(Math.max(i, 0), images.length - 1) + 1} מתוך ${images.length}`;
  };
  box.querySelector("[data-close]").addEventListener("click", () => box.remove());
  box.addEventListener("click", (e) => {
    if (e.target === box) box.remove();
  });
  document.addEventListener(
    "keydown",
    function onKey(e) {
      if (e.key === "Escape") {
        box.remove();
        document.removeEventListener("keydown", onKey);
      }
    }
  );
  track.addEventListener("scroll", update, { passive: true });
  document.body.appendChild(box);
  bindFallbackImages(box);
  requestAnimationFrame(() => {
    track.scrollTo({ left: start * track.clientWidth, behavior: "instant" });
    update();
  });
}

function confirmApproveAll() {
  const pending = lineupPieces().filter((p) => p.status !== "approved");
  if (!pending.length) {
    showToast("הכל כבר מאושר");
    return;
  }
  const box = el(`
    <div class="confirm" role="dialog" aria-modal="true">
      <div class="confirm-box">
        <p>לאשר את כל ${pending.length} הפוסטים של השבוע?</p>
        <div class="row">
          <button type="button" class="btn" data-no>ביטול</button>
          <button type="button" class="btn approve" data-yes>מאשר הכל</button>
        </div>
      </div>
    </div>`);
  box.querySelector("[data-no]").addEventListener("click", () => box.remove());
  box.querySelector("[data-yes]").addEventListener("click", async () => {
    const yes = box.querySelector("[data-yes]");
    const no = box.querySelector("[data-no]");
    yes.disabled = true;
    no.disabled = true;
    yes.textContent = "שולח…";
    try {
      state = await store.approveAll();
      box.remove();
      render();
      showToast("אושר ✓", "ok");
    } catch (err) {
      if (err instanceof AuthError) {
        box.remove();
        goLogin();
        return;
      }
      yes.disabled = false;
      no.disabled = false;
      yes.textContent = "מאשר הכל";
      showToast("השליחה נכשלה, נסה שוב", "err");
    }
  });
  document.body.appendChild(box);
}

function setComposerBusy(card, busy, busyLabel) {
  const composer = card.querySelector(".composer");
  const buttons = card.querySelectorAll("[data-act]");
  const textarea = card.querySelector("textarea");
  composer?.classList.toggle("is-sending", busy);
  buttons.forEach((b) => {
    if (busy) {
      if (!b.dataset.label) b.dataset.label = b.textContent;
      b.dataset.busy = "1";
      b.disabled = true;
      if (b === busyLabel || b.dataset.act === busyLabel) b.textContent = "שולח…";
    } else {
      b.textContent = b.dataset.label || b.textContent;
      delete b.dataset.busy;
    }
  });
  if (textarea) textarea.disabled = busy;
  if (!busy) syncSendEnabled(card);
}

async function onAction(ev) {
  const btn = ev.currentTarget;
  const code = btn.dataset.code;
  const act = btn.dataset.act;
  const card = btn.closest(".card");
  const textarea = card.querySelector("textarea");
  const text = (textarea?.value || "").trim();
  if (act === "changes" && !text) {
    textarea?.focus();
    return;
  }
  setComposerBusy(card, true, act);
  try {
    if (act === "approve") state = await store.approve(code);
    else state = await store.requestChanges(code, text);
    render();
    showToast(act === "approve" ? "אושר ✓" : "הבקשה נשלחה לצוות ✓", "ok");
  } catch (err) {
    setComposerBusy(card, false);
    if (err instanceof AuthError) goLogin();
    else showToast("השליחה נכשלה, נסה שוב", "err");
  }
}

async function loadStore(config) {
  if (config.store === "local" || !config.store) return createLocalStore(config);
  throw new Error("unknown store");
}

async function main() {
  try {
    const res = await fetch("./config.json", { cache: "no-store" });
    const config = res.ok ? await res.json() : { store: "local", apiBase: "/api" };
    document.title = config.title || document.title;
    store = await loadStore(config);
    state = await store.getState();
    render();
  } catch (err) {
    if (err instanceof AuthError || err?.status === 401) {
      goLogin();
      return;
    }
    root.innerHTML = `<p class="error-banner">לא הצלחתי לטעון את הפוסטים. רעננו את העמוד ונסו שוב.</p>`;
    console.error(err);
  }
}

main();
