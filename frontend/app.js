// AURA — app state & logic
// Recognition: tries the real backend (/v1/recognize, vision-LLM based) first.
// If the backend isn't running or fails (e.g. no ANTHROPIC_API_KEY set yet),
// falls back to a client-side mock so the UI stays testable standalone.

const BACKEND_URL = "http://localhost:8090"; // change if backend runs elsewhere
const MUSEUM_ID = "orsay";

const STR = AURA_STRINGS;
let state = {
  locale: "en",
  mode: "normal",
  visitStarted: false,
  startTime: null,
  seen: [],           // artwork ids in order
  favorites: new Set(),
  added: new Set(),
  currentArtwork: null,
  lastConfidence: 0,
  scannedIds: new Set()
};

function t(key) {
  return (STR[key] && STR[key][state.locale]) || STR[key]?.en || key;
}

function goto(id) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.getElementById(id).classList.add("active");
  if (id === "screen-progress") renderProgress();
  if (id === "screen-camera") { resetCameraView(); }
}

function applyStaticStrings() {
  document.getElementById("frameHint").textContent = t("frame_artwork");
  document.getElementById("estimateLabel").textContent = t("indicative_estimate");
  document.getElementById("whyLabel").textContent = t("why_it_matters");
  document.getElementById("whereLabel").textContent = t("where_to_look");
  document.getElementById("addLabel").textContent = t("add_to_visit");
  document.getElementById("btnStartVisit").textContent = t("start_visit");
  document.getElementById("btnShare").textContent = t("share_visit");
}

// ---------- Onboarding ----------
document.getElementById("langGrid").addEventListener("click", (e) => {
  const opt = e.target.closest(".lang-option");
  if (!opt) return;
  document.querySelectorAll(".lang-option").forEach(o => {
    o.classList.remove("selected");
    o.lastElementChild.textContent = "";
  });
  opt.classList.add("selected");
  opt.lastElementChild.textContent = "●";
  state.locale = opt.dataset.lang;
});

document.getElementById("btnContinue").addEventListener("click", () => {
  applyStaticStrings();
  goto("screen-home");
});

// ---------- Home ----------
function renderMissions() {
  const list = document.getElementById("missionsList");
  list.innerHTML = "";
  AURA_MISSIONS.forEach((m, i) => {
    const done = state.seen.length > i; // simplistic demo completion
    const row = document.createElement("div");
    row.className = "mission-item";
    row.innerHTML = `<div class="mission-badge">${done ? "✓" : i + 1}</div><div>${m[state.locale] || m.en}</div>`;
    list.appendChild(row);
  });
}

document.getElementById("btnStartVisit").addEventListener("click", () => {
  if (!state.visitStarted) {
    state.visitStarted = true;
    state.startTime = Date.now();
  }
  goto("screen-camera");
});

renderMissions();

// ---------- Camera / mock recognition ----------
let stream = null;
async function tryStartCamera() {
  const placeholder = document.getElementById("cameraPlaceholder");
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    let video = document.getElementById("liveVideo");
    if (!video) {
      video = document.createElement("video");
      video.id = "liveVideo";
      video.autoplay = true; video.playsInline = true; video.muted = true;
      video.style.cssText = "position:absolute;inset:0;width:100%;height:100%;object-fit:cover;";
      document.getElementById("cameraView").prepend(video);
    }
    video.srcObject = stream;
    placeholder.classList.add("hidden");
  } catch (err) {
    // no camera access (e.g. desktop testing) — keep placeholder, scan still works
    placeholder.classList.remove("hidden");
  }
}

function resetCameraView() {
  document.getElementById("scanStatus").textContent = "\u00A0";
  tryStartCamera();
}

function mockRecognize() {
  // Simulate confidence policy from spec §8.3 — used only when backend is unreachable.
  const unseen = AURA_ARTWORKS.filter(a => !state.scannedIds.has(a.id));
  const pool = unseen.length ? unseen : AURA_ARTWORKS;
  const artwork = pool[Math.floor(Math.random() * pool.length)];
  const confidence = 0.86 + Math.random() * 0.13;
  return { artwork, confidence };
}

function captureFrameBase64() {
  const video = document.getElementById("liveVideo");
  if (!video || !video.videoWidth) return null;
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = Math.round(512 * (video.videoHeight / video.videoWidth));
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.85).split(",")[1]; // strip data: prefix
}

async function recognizeReal(imageBase64) {
  const res = await fetch(`${BACKEND_URL}/v1/recognize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_base64: imageBase64, museum_id: MUSEUM_ID, locale: state.locale })
  });
  if (!res.ok) throw new Error("backend error " + res.status);
  const data = await res.json();
  if (data.status === "no_match" || !data.artwork_id) return { artwork: null, confidence: data.confidence };
  const artwork = AURA_ARTWORKS.find(a => a.id === data.artwork_id);
  return { artwork, confidence: data.confidence };
}

document.getElementById("btnShutter").addEventListener("click", async () => {
  const statusEl = document.getElementById("scanStatus");
  const shutter = document.getElementById("btnShutter");
  statusEl.textContent = "Analyzing…";
  shutter.style.opacity = "0.4";

  let result;
  const frame = captureFrameBase64();
  try {
    if (!frame) throw new Error("no camera frame available");
    result = await recognizeReal(frame);
  } catch (err) {
    // Backend not running / no API key yet / no camera access — fall back to mock
    result = mockRecognize();
  }

  shutter.style.opacity = "1";
  const { artwork, confidence } = result;

  if (!artwork || confidence < 0.82) {
    statusEl.textContent = t("try_again") + " — low confidence match.";
    return;
  }
  state.currentArtwork = artwork;
  state.lastConfidence = confidence;
  state.scannedIds.add(artwork.id);
  if (!state.seen.includes(artwork.id)) state.seen.push(artwork.id);
  renderCard(artwork, confidence);
  goto("screen-card");
});

// ---------- Artwork Card ----------
function renderCard(artwork, confidence) {
  document.getElementById("confidenceTag").textContent = `Matched · ${Math.round(confidence * 100)}%`;
  document.getElementById("cardImage").style.background = artwork.accent;
  document.getElementById("cardImage").textContent = artwork.image;
  document.getElementById("cardTitle").textContent = artwork.title[state.locale] || artwork.title.en;
  document.getElementById("cardArtist").textContent =
    `${artwork.artist} · ${artwork.year}` + (artwork.hall ? ` · Hall ${artwork.hall}` : "");
  document.getElementById("estimateValue").textContent =
    (artwork.estimate.low != null && artwork.estimate.high != null)
      ? `€${artwork.estimate.low}–${artwork.estimate.high}M`
      : "Pending review";

  const whyEl = document.getElementById("whyBody");
  const whereEl = document.getElementById("whereBody");
  const rarityEl = document.getElementById("rarityBody");
  const whereBlock = whereEl.closest(".section-block");
  const rarityBlock = rarityEl.closest(".section-block");
  const whyLabelEl = document.getElementById("whyLabel");

  // Content policy: some works are fully excluded from Kids mode (e.g. explicit
  // nudity) rather than given a Kids-safe rewrite. Never fall back to the
  // Normal text for these in Kids mode.
  if (state.mode === "kids" && artwork.kidsModeExcluded) {
    whyLabelEl.textContent = "";
    whyEl.textContent = t("kids_mode_excluded");
    whereBlock.style.display = "none";
    rarityBlock.style.display = "none";
  } else {
    whyLabelEl.textContent = t("why_it_matters");
    whereBlock.style.display = "";
    rarityBlock.style.display = "";
    // A few Top 20 works have a Kids-specific why/where (e.g. steering away from
    // body/violence toward myth or technique) — use it when present, otherwise
    // the same copy serves Normal/Simple/Kids.
    const whyField = (state.mode === "kids" && artwork.whyKids) ? artwork.whyKids : artwork.why;
    const whereField = (state.mode === "kids" && artwork.whereKids) ? artwork.whereKids : artwork.where;
    whyEl.textContent = whyField[state.locale] || whyField.en;
    whereEl.textContent = whereField[state.locale] || whereField.en;
    rarityEl.textContent = artwork.rarity[state.locale] || artwork.rarity.en;
  }

  document.getElementById("btnFavorite").classList.toggle("active", state.favorites.has(artwork.id));
  document.getElementById("btnFavorite").textContent = state.favorites.has(artwork.id) ? "♥" : "♡";

  const addBtn = document.getElementById("btnAdd");
  const isAdded = state.added.has(artwork.id);
  addBtn.classList.toggle("active", isAdded);
  addBtn.innerHTML = (isAdded ? "✓ " : "＋ ") +
    `<span id="addLabel">${isAdded ? t("added_to_visit") : t("add_to_visit")}</span>`;
}

document.querySelectorAll(".mode-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".mode-tab").forEach(t2 => t2.classList.remove("selected"));
    tab.classList.add("selected");
    state.mode = tab.dataset.mode;
    if (state.currentArtwork) renderCard(state.currentArtwork, state.lastConfidence);
  });
});

document.getElementById("btnFavorite").addEventListener("click", () => {
  const id = state.currentArtwork.id;
  if (state.favorites.has(id)) state.favorites.delete(id); else state.favorites.add(id);
  renderCard(state.currentArtwork, state.lastConfidence);
});

document.getElementById("btnAdd").addEventListener("click", () => {
  const id = state.currentArtwork.id;
  if (state.added.has(id)) state.added.delete(id); else state.added.add(id);
  renderCard(state.currentArtwork, state.lastConfidence);
});

document.getElementById("btnListen").addEventListener("click", (e) => {
  e.target.textContent = "▶ Listen (audio not wired in prototype)";
  setTimeout(() => (e.target.textContent = "▶ Listen"), 1800);
});

document.getElementById("btnScanNext").addEventListener("click", () => goto("screen-camera"));

document.querySelectorAll("[data-nav]").forEach(el => {
  el.addEventListener("click", () => goto(el.dataset.nav));
});

// ---------- Visit Progress ----------
function renderProgress() {
  const seenArtworks = state.seen.map(id => AURA_ARTWORKS.find(a => a.id === id));
  const artists = new Set(seenArtworks.map(a => a.artist));
  // estimate.low/high are null until an editor reviews them (§8.4, §11) —
  // unreviewed works simply don't add to the total instead of showing NaN.
  const totalLow = seenArtworks.reduce((s, a) => s + (a.estimate.low || 0), 0);
  const totalHigh = seenArtworks.reduce((s, a) => s + (a.estimate.high || 0), 0);
  const mins = state.startTime ? Math.max(1, Math.round((Date.now() - state.startTime) / 60000)) : 0;

  document.getElementById("statWorks").textContent = seenArtworks.length;
  document.getElementById("statArtists").textContent = artists.size;
  document.getElementById("statValue").textContent = (seenArtworks.length && totalHigh > 0)
    ? `€${totalLow}–${totalHigh}M` : "Pending review";
  document.getElementById("statTime").textContent = `${mins}m`;

  const pct = Math.min(100, Math.round((seenArtworks.length / AURA_ARTWORKS.length) * 100));
  document.getElementById("routeFill").style.width = pct + "%";

  const list = document.getElementById("galleryList");
  list.innerHTML = "";
  seenArtworks.slice().reverse().forEach(a => {
    const row = document.createElement("div");
    row.className = "gallery-item";
    row.innerHTML = `<div class="gallery-thumb" style="background:${a.accent}">${a.image}</div>
      <div><div class="gallery-title">${a.title[state.locale] || a.title.en}</div>
      <div class="gallery-sub">${a.artist}</div></div>`;
    list.appendChild(row);
  });
  renderMissions();
}

document.getElementById("btnContinueVisit").addEventListener("click", () => goto("screen-camera"));
document.getElementById("btnCompleteVisit").addEventListener("click", () => {
  renderRecap();
  goto("screen-recap");
});

// ---------- Recap ----------
function renderRecap() {
  const canvas = document.getElementById("recapCanvas");
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;

  const seenArtworks = state.seen.map(id => AURA_ARTWORKS.find(a => a.id === id));
  const artists = new Set(seenArtworks.map(a => a.artist));
  // estimate.low/high are null until an editor reviews them (§8.4, §11) —
  // unreviewed works simply don't add to the total instead of showing NaN.
  const totalLow = seenArtworks.reduce((s, a) => s + (a.estimate.low || 0), 0);
  const totalHigh = seenArtworks.reduce((s, a) => s + (a.estimate.high || 0), 0);
  const hasAnyEstimate = seenArtworks.some(a => a.estimate.high != null);
  const mins = state.startTime ? Math.max(1, Math.round((Date.now() - state.startTime) / 60000)) : 0;
  const favArt = seenArtworks.find(a => state.favorites.has(a.id)) || seenArtworks[0];
  const withEstimate = seenArtworks.filter(a => a.estimate.high != null);
  const mostValuable = withEstimate.length
    ? withEstimate.slice().sort((a, b) => b.estimate.high - a.estimate.high)[0]
    : favArt;

  // background
  ctx.fillStyle = "#FAFAF9";
  ctx.fillRect(0, 0, W, H);

  ctx.fillStyle = "#111111";
  ctx.font = "700 46px -apple-system, sans-serif";
  ctx.fillText("AURA", 64, 140);
  ctx.font = "500 30px -apple-system, sans-serif";
  ctx.fillStyle = "rgba(17,17,17,0.6)";
  ctx.fillText("Musée d'Orsay", 64, 186);

  // big value
  ctx.fillStyle = "#111111";
  ctx.font = "800 108px -apple-system, sans-serif";
  ctx.fillText((seenArtworks.length && hasAnyEstimate) ? `€${totalLow}–${totalHigh}M` : "Pending review", 64, 380);
  ctx.font = "600 30px -apple-system, sans-serif";
  ctx.fillStyle = "rgba(17,17,17,0.5)";
  ctx.fillText("indicative value experienced today", 64, 430);

  // stat rows
  const stats = [
    [`${seenArtworks.length}`, "masterpieces"],
    [`${artists.size}`, "artists"],
    [`${mins}m`, "in the museum"]
  ];
  let y = 560;
  stats.forEach(([num, label]) => {
    ctx.font = "800 64px -apple-system, sans-serif";
    ctx.fillStyle = "#111111";
    ctx.fillText(num, 64, y);
    ctx.font = "500 30px -apple-system, sans-serif";
    ctx.fillStyle = "rgba(17,17,17,0.55)";
    ctx.fillText(label, 260, y);
    y += 96;
  });

  if (mostValuable) {
    ctx.fillStyle = mostValuable.accent;
    roundRect(ctx, 64, y + 20, W - 128, 320, 28);
    ctx.fill();
    ctx.fillStyle = "#fff";
    ctx.font = "700 34px -apple-system, sans-serif";
    wrapText(ctx, mostValuable.title[state.locale] || mostValuable.title.en, 100, y + 100, W - 200, 42);
    ctx.font = "500 26px -apple-system, sans-serif";
    ctx.globalAlpha = 0.85;
    ctx.fillText(mostValuable.artist, 100, y + 150);
    ctx.globalAlpha = 1;
    ctx.font = "800 44px -apple-system, sans-serif";
    ctx.fillText(
      mostValuable.estimate.high != null
        ? `€${mostValuable.estimate.low}–${mostValuable.estimate.high}M`
        : "Estimate pending review",
      100, y + 260
    );
    ctx.font = "600 24px -apple-system, sans-serif";
    ctx.globalAlpha = 0.85;
    ctx.fillText(mostValuable.estimate.high != null ? "Most valuable seen today" : "Featured today", 100, y + 300);
    ctx.globalAlpha = 1;
  }

  ctx.fillStyle = "rgba(17,17,17,0.35)";
  ctx.font = "600 26px -apple-system, sans-serif";
  ctx.fillText("Point. Discover. Understand.", 64, H - 80);
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}
function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
  const words = text.split(" ");
  let line = "", cy = y;
  words.forEach(w => {
    const test = line + w + " ";
    if (ctx.measureText(test).width > maxWidth && line) {
      ctx.fillText(line, x, cy);
      line = w + " ";
      cy += lineHeight;
    } else line = test;
  });
  ctx.fillText(line, x, cy);
}

document.getElementById("btnSavePng").addEventListener("click", () => {
  const canvas = document.getElementById("recapCanvas");
  const link = document.createElement("a");
  link.download = "aura-visit-recap.png";
  link.href = canvas.toDataURL("image/png");
  link.click();
});

document.getElementById("btnShare").addEventListener("click", async () => {
  const canvas = document.getElementById("recapCanvas");
  canvas.toBlob(async (blob) => {
    const file = new File([blob], "aura-visit-recap.png", { type: "image/png" });
    if (navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
      try { await navigator.share({ files: [file], title: "My AURA visit" }); } catch (e) {}
    } else {
      document.getElementById("btnSavePng").click();
    }
  });
});

document.getElementById("btnNewVisit").addEventListener("click", () => {
  state = { locale: state.locale, mode: "normal", visitStarted: false, startTime: null,
            seen: [], favorites: new Set(), added: new Set(), currentArtwork: null,
            lastConfidence: 0, scannedIds: new Set() };
  renderMissions();
  goto("screen-home");
});

// ---------- PWA service worker ----------
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  });
}
