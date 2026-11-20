"use strict";
const $ = (selector) => document.querySelector(selector);
const state = {
  token: "",
  config: null,
  id: null,
  detail: null,
  words: [],
  page: 0,
  candidatePage: 0,
  busy: false,
  tab: "clips",
  selected: new Set(),
  noticeTimer: null,
  captionDraft: null,
  captionKey: "",
  captionSerial: 0,
  captionPreset: "default",
  previewFile: null,
  pendingPreview: null,
};
const escapeHTML = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const basename = (source) =>
  source.split(/[\\/]/).filter(Boolean).pop() || source;
const projectName = (source) =>
  /^https?:/.test(source)
    ? source.replace(/^https?:\/\//, "").slice(0, 65)
    : basename(source);
function notice(message, error = false) {
  clearTimeout(state.noticeTimer);
  const box = $("#notice");
  box.hidden = false;
  box.textContent = message;
  box.classList.toggle("error", error);
  state.noticeTimer = setTimeout(
    () => {
      box.hidden = true;
    },
    error ? 15000 : 6000,
  );
}
async function api(path, data) {
  const response = await fetch(
    path,
    data === undefined
      ? {}
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Chopify-Token": state.token,
          },
          body: JSON.stringify(data),
        },
  );
  const result = await response.json();
  if (!response.ok)
    throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}
function safe(handler) {
  return async (event) => {
    try {
      await handler(event);
    } catch (error) {
      notice(error.message, true);
    }
  };
}
async function config() {
  state.config = await api("/api/config");
  const ownerSelect = $("#new-source-owner");
  if (ownerSelect) {
    for (const owner of state.config.source_owners || []) {
      const opt = document.createElement("option");
      opt.value = owner.value;
      opt.textContent = owner.label;
      ownerSelect.append(opt);
    }
  }
  state.token = state.config.token;
  updatePresets();
  updateBrands();
  renderCaptionGallery();
  updateSystemBadges().catch(() => {});
}
async function updateSystemBadges() {
  const hw = $("#hardware-badge");
  const gpu = state.config?.detected_gpu;
  const vp = state.config?.detected_vision_preset;
  if (hw && vp) {
    const gpuLabel = gpu?.gpu_name
      ? `${gpu.gpu_name} (${gpu.vram_mib} MiB)`
      : "CPU only";
    hw.textContent = `GPU: ${gpuLabel} · Preset: ${String(vp.preset || "low").toUpperCase()}`;
    hw.title = JSON.stringify(vp.models || {}, null, 2);
  }
  const dbEl = $("#db-badge");
  if (dbEl) {
    try {
      const db = await api("/api/db/status");
      const sources = db.total_sources ?? db.sources ?? 0;
      const clips = db.total_clips ?? db.clips ?? 0;
      dbEl.textContent = `DB: OK · ${sources} fontes · ${clips} cortes`;
    } catch {
      dbEl.textContent = "DB: offline";
    }
  }
}
function presetNames() {
  return Object.keys(state.config.caption_presets || {});
}
function updatePresets() {
  const markup = presetNames()
    .map((name) => `<option>${escapeHTML(name)}</option>`)
    .join("");
  for (const select of [
    $("#new-style"),
    $("#caption-preset"),
    $("#settings-form").elements.style,
  ]) {
    if (!select) continue;
    const current = select.value;
    select.innerHTML = markup;
    if (presetNames().includes(current)) select.value = current;
  }
}
function aspectCaptionBase(aspect) {
  return (
    state.config.caption_aspects[aspect] ||
    state.config.caption_aspects["16:9"] || { font_size: 72, margin: 95 }
  );
}
function brandCaption(name) {
  return (state.config.caption_brands || {})[name] || {};
}
function savedCaptionStyle() {
  const options = state.detail.project.options;
  const brand = options.brand
    ? basename(options.brand).replace(/\.json$/, "")
    : "";
  const base = aspectCaptionBase(options.aspect);
  const merged = {
    ...state.config.caption_defaults,
    ...(state.config.caption_presets[options.style] || {}),
    ...brandCaption(brand),
    ...(options.caption || {}),
  };
  if (merged.font_size == null) merged.font_size = base.font_size;
  if (merged.margin == null) merged.margin = base.margin;
  return merged;
}
function captionFromForm() {
  const form = $("#caption-form");
  const value = (name) => form.elements[name].value;
  return {
    font: value("font").trim() || "Arial Black",
    font_size: Number(value("font_size")),
    color: value("color"),
    highlight: value("highlight"),
    emphasis_color: value("emphasis_color"),
    outline_color: value("outline_color"),
    uppercase: form.elements.uppercase.checked,
    words_per_cue: Number(value("words_per_cue")),
    position: value("position"),
    margin: Number(value("margin")),
    outline: Number(value("outline")),
    shadow: Number(value("shadow")),
    background: value("background"),
    background_color: value("background_color"),
    background_opacity: Number(value("background_opacity")),
    animation: value("animation"),
    highlight_mode: value("highlight_mode"),
    emoji: form.elements.emoji.checked,
    emphasis: form.elements.emphasis.checked,
  };
}
function fillCaptionForm(style, preset) {
  const form = $("#caption-form");
  for (const [key, value] of Object.entries(style)) {
    const input = form.elements.namedItem(key);
    if (!input) continue;
    if (input.type === "checkbox") input.checked = !!value;
    else input.value = value ?? "";
  }
  $("#caption-preset").value = preset;
  state.captionDraft = captionFromForm();
  state.captionSerial++;
  state.captionKey = "";
  updateCaptionSummary();
  updateCaptionOverlay();
}
function syncCaption() {
  if (!state.detail) return;
  state.captionDraft = captionFromForm();
  state.captionSerial++;
  state.captionKey = "";
  updateCaptionSummary();
  updateCaptionOverlay();
}
function updateCaptionSummary() {
  const style = state.captionDraft;
  if (!style) return;
  $("#caption-summary").textContent =
    `${style.words_per_cue} words · ${style.position} · ` +
    `${style.animation === "none" ? "no motion" : style.animation}`;
}
function renderCaptionGallery() {
  const wrap = $("#caption-presets");
  if (!wrap) return;
  wrap.innerHTML = presetNames()
    .map(
      (name) =>
        `<button type="button" class="caption-preset" data-caption-preset="${escapeHTML(name)}" aria-pressed="false">${escapeHTML(name)}</button>`,
    )
    .join("");
  for (const button of wrap.querySelectorAll("[data-caption-preset]")) {
    const preset = state.config.caption_presets[button.dataset.captionPreset];
    button.style.setProperty("--preset-font", preset.font);
    button.style.setProperty("--preset-color", preset.color);
    button.style.setProperty("--preset-highlight", preset.highlight);
  }
  markCaptionPreset(state.captionPreset);
}
function markCaptionPreset(name) {
  state.captionPreset = name;
  for (const button of document.querySelectorAll("[data-caption-preset]"))
    button.setAttribute(
      "aria-pressed",
      String(button.dataset.captionPreset === name),
    );
}
function applyCaptionPreset(name) {
  if (!state.detail || !state.config.caption_presets[name]) return;
  const base = aspectCaptionBase(state.detail.project.options.aspect);
  const style = { ...state.config.caption_defaults, ...state.config.caption_presets[name] };
  if (style.font_size == null) style.font_size = base.font_size;
  if (style.margin == null) style.margin = base.margin;
  fillCaptionForm(style, name);
  $("#settings-form").elements.style.value = name;
  markCaptionPreset(name);
}
function hexToRgba(hex, opacity) {
  const match = /^#([0-9a-f]{6})$/i.exec(String(hex));
  if (!match) return "rgba(0, 0, 0, 0.7)";
  const value = parseInt(match[1], 16);
  const alpha = Math.max(0, Math.min(100, Number(opacity) || 0)) / 100;
  return `rgba(${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}, ${alpha})`;
}
function isEmphasizedWord(text) {
  const plain = String(text)
    .trim()
    .replace(/^[^\w$€£¥]+|[^\w%$€£¥]+$/g, "");
  if (!plain) return false;
  if (/[\d$€£¥]/.test(plain)) return true;
  if (plain.length > 2 && plain === plain.toUpperCase() && /[A-Z]/.test(plain))
    return true;
  return state.config.caption_power_words.includes(
    plain.toLowerCase().replace(/[.,!?;:'"]+$/, ""),
  );
}
function emojiForWord(text) {
  const token = String(text)
    .toLowerCase()
    .replace(/[^a-z0-9']/g, "");
  if (!token) return "";
  for (const rule of state.config.caption_emoji_rules || [])
    if (rule.words.some((stem) => token.startsWith(stem))) return rule.emoji;
  return "";
}
function updateCaptionOverlay(force = false) {
  const overlay = $("#caption-overlay"),
    player = $("#source-player"),
    style = state.captionDraft;
  if (
    !state.detail ||
    !state.detail.transcript ||
    state.detail.playable_source === false ||
    state.previewFile ||
    state.tab !== "captions" ||
    !style
  ) {
    overlay.hidden = true;
    return;
  }
  const words = state.words.filter((item) => !item.hidden);
  const per = Math.max(1, Math.min(8, Number(style.words_per_cue) || 3));
  const current = player.currentTime || 0;
  let cue = null,
    cueIndex = -1;
  for (let i = 0; i < words.length; i += per) {
    const group = words.slice(i, i + per);
    if (
      group.length &&
      current >= group[0].start &&
      current <= group[group.length - 1].end
    ) {
      cue = group;
      cueIndex = i;
      break;
    }
  }
  if (!cue) {
    overlay.hidden = true;
    return;
  }
  let active = 0;
  for (let i = 0; i < cue.length; i++) if (current >= cue[i].start) active = i;
  const marked = [];
  for (let i = 0; i < cue.length; i++)
    if (cue[i].emphasis === true) marked.push(i);
  if (style.emphasis)
    for (let i = 0; i < cue.length; i++)
      if (!marked.includes(i) && isEmphasizedWord(cue[i].word)) marked.push(i);
  const emphasised = new Set(marked.slice(0, 2));
  let emojiIndex = -1,
    emoji = "";
  if (style.emoji) {
    for (let i = 0; i < cue.length; i++) {
      emoji = emojiForWord(cue[i].word);
      if (emoji) {
        emojiIndex = i;
        break;
      }
    }
  }
  const key = `${cueIndex}:${active}:${state.captionSerial}`;
  if (state.captionKey !== key || force) {
    const parts = [];
    cue.forEach((item, i) => {
      if (style.animation === "typewriter" && i > active) return;
      let token = escapeHTML(
        style.uppercase ? item.word.toUpperCase() : item.word,
      );
      if (i === emojiIndex) token += ` <span class="caption-emoji">${emoji}</span>`;
      let className = "caption-word";
      if (style.highlight_mode !== "none" && i === active)
        className += " is-active";
      else if (style.highlight_mode === "karaoke" && i < active)
        className += " is-karaoke";
      else if (style.highlight_mode !== "none" && emphasised.has(i))
        className += " is-emphasis";
      if (
        i === active &&
        style.animation !== "none" &&
        style.animation !== "typewriter"
      )
        className += ` is-${style.animation}`;
      parts.push(`<span class="${className}">${token}</span>`);
    });
    $("#caption-cue").innerHTML = parts.join(" ");
    state.captionKey = key;
  }
  const wrap = $(".player-wrap");
  const scale = Math.max(0.04, (wrap.clientHeight || 1) / 1080);
  const set = (name, value) => overlay.style.setProperty(name, value);
  overlay.className =
    `caption-overlay caption-${style.position}` +
    (style.background === "box" ? " caption-boxed" : "");
  set("--caption-font", `${style.font}, "Segoe UI Emoji", sans-serif`);
  set("--caption-font-size", `${Math.max(8, style.font_size * scale)}px`);
  set("--caption-margin", `${Math.max(0, style.margin * scale)}px`);
  set("--caption-outline", `${Math.max(0, style.outline * scale)}px`);
  set("--caption-shadow", `${Math.max(0, style.shadow * scale)}px`);
  set("--caption-color", style.color);
  set("--caption-highlight", style.highlight);
  set("--caption-emphasis", style.emphasis_color);
  set("--caption-outline-color", style.outline_color);
  set(
    "--caption-box-bg",
    hexToRgba(style.background_color, style.background_opacity),
  );
  set("--caption-box-pad", `${Math.max(2, style.outline * scale + 2)}px`);
  overlay.hidden = false;
}
function updateBrands(selected = "") {
  $("#brand-select").innerHTML =
    '<option value="">Use caption style</option>' +
    state.config.brands
      .map(
        (name) =>
          `<option value="${escapeHTML(name)}">${escapeHTML(name)}</option>`,
      )
      .join("");
  $("#brand-select").value = selected;
}
async function refreshProjects() {
  const result = await api("/api/projects");
  $("#project-count").textContent = result.projects.length;
  const markup = result.projects.length
    ? result.projects
        .map(
          (p) =>
            `<button class="project-item ${p.id === state.id ? "active" : ""}" data-id="${p.id}"><strong>${escapeHTML(projectName(p.source))}</strong><small>${escapeHTML(p.status)} · ${escapeHTML(p.stage)}</small></button>`,
        )
        .join("")
    : '<p class="muted">Add a recording to begin.</p>';
  // Preserve keyboard focus while polling unchanged projects.
  if (state.projectMarkup !== markup) {
    $("#projects").innerHTML = markup;
    state.projectMarkup = markup;
  }
}
async function selectProject(id) {
  state.id = id;
  state.page = 0;
  state.candidatePage = 0;
  state.tab = "clips";
  state.captionDraft = null;
  state.captionKey = "";
  state.previewFile = null;
  state.pendingPreview = null;
  $("#new-view").hidden = true;
  $("#project-view").hidden = false;
  const detail = await api(`/api/projects/${id}`);
  if (state.id !== id) return;
  state.detail = detail;
  state.words = structuredClone(state.detail.transcript?.words || []);
  state.selected = new Set(state.detail.candidates.map((_, i) => i + 1));
  renderDetail();
  await refreshProjects();
}
function updateStatus(detail) {
  const progress = detail.progress || {};
  const total = Number(progress.total);
  const progressText =
    detail.busy && progress.stage && Number.isFinite(total) && total > 0
      ? ` · ${progress.stage} ${Number(progress.done) || 0}/${total}`
      : "";
  $("#status").textContent =
    `${detail.project.status} · ${detail.project.stage}${progressText}`;
  const errors = detail.render_errors || [];
  const error =
    detail.project.error ||
    (errors.length ? `${errors.length} clip(s) failed to render.` : "");
  $("#job-error").hidden = !error;
  $("#job-error").textContent = error;
  $("#log").textContent = detail.log || "No job has run yet.";
  state.busy = detail.busy;
  for (const selector of [
    "#prepare",
    "#preview",
    "#render",
    "#save-candidates",
    "#save-transcript",
  ])
    $(selector).disabled = detail.busy;
  for (const el of document.querySelectorAll(
    "#settings-form button, #caption-form button, #caption-preview",
  ))
    el.disabled = detail.busy;
  for (const el of document.querySelectorAll(
    "#settings-form input, #settings-form select, #candidates input, #transcript-words input, #caption-form input, #caption-form select, #caption-presets button",
  ))
    el.disabled = detail.busy;
}
const CANDIDATES_PER_PAGE = 25;
const CONTENT_PROFILE_LABELS = {
  talk: "podcast/talk",
  mixed: "mixed footage",
  "gameplay/action": "gameplay/action",
};
function formatDuration(seconds) {
  const total = Number(seconds);
  if (!Number.isFinite(total) || total <= 0) return "0s";
  if (total < 10) return `${Math.round(total * 10) / 10}s`;
  if (total < 60) return `${Math.round(total * 10) / 10}s`;
  const whole = Math.round(total);
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const remainder = whole % 60;
  if (hours)
    return `${hours}h ${String(minutes).padStart(2, "0")}m`;
  return `${minutes}m ${String(remainder).padStart(2, "0")}s`;
}
function renderSelectionSummary(detail) {
  const box = $("#selection-summary");
  const selection = detail.selection || {};
  const candidates = detail.candidates || [];
  const scores = candidates
    .map((item) => Number(item.overall))
    .filter(Number.isFinite);
  const minScore = Number(
    selection.min_score ?? detail.project.options.min_score ?? 8,
  );
  const passing = Number.isFinite(Number(selection.passing))
    ? Number(selection.passing)
    : scores.filter((score) => score >= minScore).length;
  const scoreLow = Number.isFinite(Number(selection.score_min))
    ? Number(selection.score_min)
    : scores.length
      ? Math.min(...scores)
      : null;
  const scoreHigh = Number.isFinite(Number(selection.score_max))
    ? Number(selection.score_max)
    : scores.length
      ? Math.max(...scores)
      : null;
  const passingScores = scores.filter((score) => score >= minScore);
  const passLow = Number.isFinite(Number(selection.passing_score_min))
    ? Number(selection.passing_score_min)
    : passingScores.length
      ? Math.min(...passingScores)
      : null;
  const passHigh = Number.isFinite(Number(selection.passing_score_max))
    ? Number(selection.passing_score_max)
    : passingScores.length
      ? Math.max(...passingScores)
      : null;
  const durations = candidates
    .map((item) => Number(item.duration ?? item.end - item.start))
    .filter((value) => Number.isFinite(value) && value >= 0);
  const durationLow = Number.isFinite(Number(selection.duration_min))
    ? Number(selection.duration_min)
    : durations.length
      ? Math.min(...durations)
      : null;
  const durationHigh = Number.isFinite(Number(selection.duration_max))
    ? Number(selection.duration_max)
    : durations.length
      ? Math.max(...durations)
      : null;
  const lines = [];
  if (!passing) {
    lines.push(
      scoreLow === null || scoreHigh === null
        ? "No scored candidates yet."
        : `Candidate scores ${scoreLow.toFixed(1)}-${scoreHigh.toFixed(1)}.`,
    );
    lines.push(
      `No clips at ${minScore.toFixed(1)}+. Lower the minimum score to review more.`,
    );
  } else {
    const range =
      passLow === null || passHigh === null
        ? ""
        : ` · passing scores ${passLow.toFixed(1)}-${passHigh.toFixed(1)}`;
    const length =
      durationLow === null || durationHigh === null
        ? ""
        : ` · ${formatDuration(durationLow)}-${formatDuration(durationHigh)}`;
    lines.push(`${passing} clips at ${minScore.toFixed(1)}+${range}${length}`);
    const profile =
      CONTENT_PROFILE_LABELS[selection.content_profile] ||
      selection.content_profile;
    if (profile) lines.push(`Footage: ${profile}`);
  }
  box.textContent = lines.join("\n");
  box.hidden = false;
}
function renderDetail() {
  const detail = state.detail,
    p = detail.project,
    options = p.options;
  $("#project-id").textContent = `PROJECT / ${p.id}`;
  $("#project-title").textContent = projectName(p.source);
  $("#project-source").textContent = p.source;
  const player = $("#source-player");
  const hint = $("#player-hint");
  if (detail.playable_source) {
    player.hidden = !detail.transcript;
    hint.hidden = !!detail.transcript;
    hint.textContent = "Prepare this project to preview the source.";
    const source = `/media/${p.id}/source`;
    if (detail.transcript && player.getAttribute("src") !== source)
      player.src = source;
  } else if (state.previewFile) {
    player.hidden = false;
    hint.hidden = true;
    if (player.getAttribute("src") !== state.previewFile.url)
      player.src = state.previewFile.url;
  } else {
    player.hidden = true;
    hint.hidden = false;
    hint.textContent = detail.transcript
      ? "Long source: press Watch on a clip to render a 480p preview from a downloaded section."
      : "Prepare this project to preview the source.";
  }
  const form = $("#settings-form");
  for (const [key, value] of Object.entries(options)) {
    const input = form.elements.namedItem(key);
    if (input) {
      if (input.type === "checkbox") input.checked = value;
      else input.value = value ?? "";
    }
  }
  form.elements.center1.value = options.centers[0];
  form.elements.center2.value = options.centers[1];
  const brand = options.brand
    ? basename(options.brand).replace(/\.json$/, "")
    : "";
  updateBrands(brand);
  $("#search-mode").value = options.semantic
    ? "semantic"
    : options.search
      ? "search"
      : "auto";
  $("#query").value = options.semantic || options.search || "";
  fillCaptionForm(savedCaptionStyle(), options.style);
  markCaptionPreset(options.style);
  $("#candidate-count").textContent = detail.candidates.length;
  const total = detail.candidates.length;
  const pageCount = Math.max(1, Math.ceil(total / CANDIDATES_PER_PAGE));
  state.candidatePage = Math.min(Math.max(0, state.candidatePage), pageCount - 1);
  const start = state.candidatePage * CANDIDATES_PER_PAGE;
  const visible = detail.candidates.slice(start, start + CANDIDATES_PER_PAGE);
  $("#candidates").innerHTML = visible.length
    ? visible
        .map((c, offset) => {
          const i = start + offset;
          const rank = Number.isFinite(Number(c.rank)) ? Number(c.rank) : i + 1;
          const duration = Number(c.duration ?? c.end - c.start);
          const aiTitle = c.proposed_title
            ? `<div class="candidate-ai-line"><b>Título IA:</b> ${escapeHTML(c.proposed_title)}</div>`
            : "";
          const aiBanner = c.context_banner_2s
            ? `<div class="candidate-ai-line"><b>Faixa 2s:</b> ${escapeHTML(c.context_banner_2s)}</div>`
            : "";
          const aiComment = c.pinned_comment_debate
            ? `<div class="candidate-ai-line"><b>1º Comentário:</b> ${escapeHTML(c.pinned_comment_debate)}</div>`
            : "";
          const aiBadge = c.llm_mode_used
            ? ` · IA: ${escapeHTML(String(c.llm_mode_used))}`
            : "";
          const tierPill = c.tier
            ? ` <span class="pill-tier pill-tier-${escapeHTML(String(c.tier).toLowerCase())}">${escapeHTML(String(c.tier).toUpperCase())}</span>`
            : "";
          const archPill = c.archetype
            ? ` <span class="pill-arch">${escapeHTML(String(c.archetype))}</span>`
            : "";
          return `<article class="candidate" data-index="${i}"><input type="checkbox" aria-label="Select clip ${i + 1}" data-select="${i + 1}" ${state.selected.has(i + 1) ? "checked" : ""}><div><div class="candidate-title"><input aria-label="Clip ${i + 1} title" data-field="hook" value="${escapeHTML(c.hook)}"></div><div class="candidate-meta">#${rank} · ${Number(c.overall).toFixed(1)}/10 · ${formatDuration(duration)}${aiBadge}${tierPill}${archPill}${c.similarity !== undefined ? " · SEMANTIC " + Number(c.similarity).toFixed(2) : ""}</div>${aiTitle}${aiBanner}${aiComment}<div class="candidate-time"><label>Start (seconds)<input data-field="start" type="number" min="0" step="0.01" value="${c.start}"></label><label>End (seconds)<input data-field="end" type="number" min="0" step="0.01" value="${c.end}"></label></div><details class="candidate-reason"><summary>Why this clip</summary><p>${escapeHTML(c.reason || "")}</p><pre>${escapeHTML(JSON.stringify(c.score_parts || {}, null, 2))}</pre>${c.evidence ? `<pre>${escapeHTML(JSON.stringify(c.evidence, null, 2))}</pre>` : ""}</details></div><button data-play="${i}">▶ Watch</button></article>`;
        })
        .join("")
    : '<p class="muted">Find clips to see candidates here. You can adjust selection and timing before export.</p>';
  $("#candidate-page").textContent =
    `${total ? start + 1 : 0}–${Math.min(start + CANDIDATES_PER_PAGE, total)} of ${total}`;
  $("#candidates-prev").disabled = state.candidatePage === 0;
  $("#candidates-next").disabled = start + CANDIDATES_PER_PAGE >= total;
  renderSelectionSummary(detail);
  renderWords();
  updateSelection();
  renderOutputs(detail);
  updateStatus(detail);
  setTab(state.tab);
}
function setTab(tab) {
  state.tab = tab;
  $("#clip-panel").hidden = tab !== "clips";
  $("#transcript-panel").hidden = tab !== "transcript";
  $("#caption-panel").hidden = tab !== "captions";
  $("#show-clips").setAttribute("aria-pressed", String(tab === "clips"));
  $("#show-transcript").setAttribute(
    "aria-pressed",
    String(tab === "transcript"),
  );
  $("#show-captions").setAttribute(
    "aria-pressed",
    String(tab === "captions"),
  );
  state.captionKey = "";
  updateCaptionOverlay(true);
}
function updateSelection() {
  $("#selection-count").textContent = `${state.selected.size} selected`;
}
function renderWords() {
  const start = state.page * 100,
    visible = state.words.slice(start, start + 100);
  $("#transcript-words").innerHTML = visible.length
    ? '<div class="word-header"><span></span><span>WORD</span><span>START (S)</span><span>END (S)</span></div>' +
      visible
        .map(
          (word, i) =>
            `<div class="word-row" data-word="${start + i}"><button data-seek="${start + i}" aria-label="Play word ${start + i + 1}">${start + i + 1}</button><input aria-label="Word ${start + i + 1}" data-word-field="word" value="${escapeHTML(word.word)}"><input aria-label="Word ${start + i + 1} start" data-word-field="start" type="number" min="0" step="0.01" value="${word.start}"><input aria-label="Word ${start + i + 1} end" data-word-field="end" type="number" min="0" step="0.01" value="${word.end}"></div>`,
        )
        .join("")
    : '<p class="muted">Prepare the project to get an editable transcript.</p>';
  $("#word-page").textContent =
    `${state.words.length ? start + 1 : 0}–${Math.min(start + 100, state.words.length)} of ${state.words.length} words`;
  $("#words-prev").disabled = state.page === 0;
  $("#words-next").disabled = start + 100 >= state.words.length;
  for (const el of document.querySelectorAll("#transcript-words input"))
    el.disabled = state.busy;
}
const PUBLISH_PLATFORMS = [
  { id: "youtube_shorts", short: "YT", label: "YouTube Shorts" },
  { id: "tiktok", short: "TT", label: "TikTok" },
  { id: "instagram_reels", short: "IG", label: "Reels" },
  { id: "facebook_reels", short: "FB", label: "Facebook" },
];
const outputPlatformState = new Map();

async function copyToClipboard(text, label) {
  try {
    await navigator.clipboard.writeText(text);
    notice(`${label} copiado!`);
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
    notice(`${label} copiado!`);
  }
}

function renderPublishBox(stem, kit, postedMap, cooldowns, verdict) {
  if (!kit || !kit.platforms) return "";
  const activePlat = outputPlatformState.get(stem) || "youtube_shorts";
  const platData = kit.platforms[activePlat] || kit.platforms.youtube_shorts;
  const isPosted = !!(postedMap && postedMap[activePlat]);
  const streamerLabel = kit.streamer?.display_name || "";
  const cdInfo = cooldowns && cooldowns[activePlat];
  // Selo P1 vem SÓ do veredito do RiskShield (risk_seal.js): sem veredito, nunca aparece como blindado.
  const seal = riskSeal(verdict, activePlat, cdInfo);
  const auditBadge = `<span class="risk-pill ${seal.cls}" title="${escapeHTML(seal.title || "")}">${escapeHTML(seal.label)}</span>`;
  const cooldownBtn = cdInfo
    ? `<button type="button" class="pub-btn" data-cooldown-clear="${activePlat}">▶ Encerrar Cool-Down</button>`
    : `<button type="button" class="pub-btn" data-cooldown="${activePlat}" title="Trava novas postagens nesta rede por 48h">⏸ Cool-Down 48h</button>`;
  const tabsHtml = PUBLISH_PLATFORMS.map((p) => {
    const done = !!(postedMap && postedMap[p.id]);
    const inCd = !!(cooldowns && cooldowns[p.id]);
    return `<button type="button" class="pub-tab ${p.id === activePlat ? "active" : ""} ${done ? "is-posted" : ""}" data-pub-tab="${p.id}" data-stem="${escapeHTML(stem)}">${p.short}${done ? " ✓" : inCd ? " ⏸" : ""}</button>`;
  }).join("");
  const titleBtn =
    activePlat === "youtube_shorts"
      ? `<button type="button" class="pub-btn" data-copy-field="title" data-stem="${escapeHTML(stem)}">📋 Título</button>`
      : "";
  const descLabel = activePlat === "youtube_shorts" ? "📋 Descrição" : "📋 Legenda";
  const commentBtn =
    platData?.pinned_comment && activePlat === "youtube_shorts"
      ? `<button type="button" class="pub-btn" data-copy-field="pinned_comment" data-stem="${escapeHTML(stem)}">📋 1º Comentário</button>`
      : "";
  const postedBadge = isPosted
    ? `<span class="pub-posted-tag">✓ Postado</span>`
    : `<button type="button" class="pub-btn pub-btn-done" data-mark-posted="${activePlat}" data-stem="${escapeHTML(stem)}">✅ Marcar postado</button>`;
  return `<div class="publish-kit" data-pub-stem="${escapeHTML(stem)}">
    <div class="pub-head">
      <div class="pub-badges">${streamerLabel ? `<span class="pub-streamer">${escapeHTML(streamerLabel)}</span>` : ""}${auditBadge}</div>
      <div class="pub-tabs">${tabsHtml}</div>
    </div>
    <div class="pub-actions">
      ${titleBtn}
      <button type="button" class="pub-btn" data-copy-field="description" data-stem="${escapeHTML(stem)}">${descLabel}</button>
      ${commentBtn}
      <a class="pub-btn pub-link" href="${escapeHTML(platData?.upload_url || "#")}" target="_blank" rel="noopener">↗ Abrir upload</a>
      ${postedBadge}
      ${cooldownBtn}
    </div>
    ${riskXray(verdict)}
  </div>`;
}

function renderOutputs(detail) {
  const videos = detail.files.filter((f) => f.name.endsWith(".mp4"));
  const exportedVideos = videos.filter((f) => f.kind === "clips");
  const bundleBtn = $("#export-daily-bundle");
  if (bundleBtn) bundleBtn.hidden = exportedVideos.length === 0;
  $("#output-count").textContent = `${videos.length} CLIPS`;
  $("#outputs").className = videos.length ? "output-grid" : "";
  const kits = detail.publish_kits || {};
  const pubs = detail.publications || {};
  $("#outputs").innerHTML = videos.length
    ? videos
        .map((file) => {
          const stem = file.name.slice(0, -4),
            hasOfficialThumb = detail.files.some(
              (f) => f.kind === file.kind && f.name === stem + "_thumb.png",
            ),
            related = detail.files.filter(
              (f) =>
                f.kind === file.kind &&
                [
                  stem + ".srt",
                  ...(hasOfficialThumb ? [stem + "_thumb.png"] : [stem + ".png"]),
                  stem + ".meta.json",
                ].includes(f.name),
            ),
            thumbFile =
              detail.files.find(
                (f) => f.kind === file.kind && f.name === stem + "_thumb.png",
              ) ||
              detail.files.find(
                (f) => f.kind === file.kind && f.name === stem + ".png",
              ),
            posterAttr = thumbFile ? ` poster="${encodeURI(thumbFile.url)}"` : "",
            viewThumbLink = thumbFile
              ? `<a href="${encodeURI(thumbFile.url)}" target="_blank" rel="noopener">VER THUMB ↗</a>`
              : "",
            folderBtn = `<button type="button" class="link-btn" data-open-folder="${escapeHTML(file.name)}" data-kind="${escapeHTML(file.kind)}">📂 PASTA</button>`,
            pubHtml =
              file.kind === "clips"
                ? renderPublishBox(stem, kits[stem], pubs[stem], detail.cooldowns || {},
                    (detail.risk_verdicts || {})[stem] || null)
                : '<p class="draft-pub-hint">Rascunho 480p · Clique em <strong>Export selected ↗</strong> para liberar os botões YT/TT/IG/FB e o Pacote do Dia.</p>';
          return `<article class="output-card"><video controls preload="none"${posterAttr} src="${encodeURI(file.url)}"></video><div class="output-info"><p>${escapeHTML(file.kind === "previews" ? "DRAFT · " : "EXPORT · ")}${escapeHTML(stem)}</p><div class="output-links"><a href="${encodeURI(file.url)}" download>MP4 ↓</a>${viewThumbLink}${related.map((f) => `<a href="${encodeURI(f.url)}" download>${f.name.endsWith(".srt") ? "SRT" : f.name.endsWith(".png") ? "THUMB" : "META"} ↓</a>`).join("")}${folderBtn}</div>${pubHtml}</div></article>`;
        })
        .join("")
    : '<p class="muted">Choose candidates and make a preview or export.</p>';
}
async function saveCandidates(showNotice = true) {
  if (!state.detail.candidates.length)
    throw new Error("Find clips before exporting.");
  await api(`/api/projects/${state.id}/candidates`, {
    candidates: state.detail.candidates,
  });
  if (showNotice) notice("Clip edits saved.");
}
async function run(action, preview = false) {
  if (action === "render") {
    if (!state.selected.size) throw new Error("Select at least one clip.");
    await saveCandidates(false);
  }
  await api(`/api/projects/${state.id}/run`, {
    action,
    preview,
    pick:
      action === "render"
        ? [...state.selected].sort((a, b) => a - b).join(",")
        : null,
  });
  state.detail.busy = true;
  state.detail.project.status = "queued";
  state.detail.project.stage = action;
  updateStatus(state.detail);
  notice(
    action === "prepare"
      ? "Queued. Saved stages will be reused when their inputs match."
      : "Queued selected clips.",
  );
  await refreshProjects();
}
$("#new-project").addEventListener("click", () => {
  state.id = null;
  $("#new-view").hidden = false;
  $("#project-view").hidden = true;
  $("#sources").focus();
  refreshProjects().catch((e) => notice(e.message, true));
});
$("#projects").addEventListener(
  "click",
  safe(async (event) => {
    const button = event.target.closest("[data-id]");
    if (button) await selectProject(button.dataset.id);
  }),
);
$("#create-form").addEventListener(
  "submit",
  safe(async (event) => {
    event.preventDefault();
    const sources = $("#sources")
      .value.split(/\r?\n/)
      .map((s) => s.trim().replace(/^"|"$/g, ""))
      .filter(Boolean);
    if (!sources.length) throw new Error("Add a video path or URL.");
    const button = event.target.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      const chosenAspect = $("#new-aspect").value;
      const options = {
        aspect: chosenAspect,
        layout: $("#new-layout")?.value || "single",
        max_len: chosenAspect === "9:16" ? 58 : 300,
        whisper_model: $("#new-model").value,
        style: $("#new-style").value,
        ai_mode: $("#new-ai-mode")?.value || "heuristic",
        vision_preset: $("#new-vision-preset")?.value || "auto",
      };
      const owner = $("#new-source-owner")?.value;
      if (owner) options.source_owner = owner;
      const result = await api("/api/batch", { sources, options });
      await selectProject(result.projects[0].id);
      notice(
        `${sources.length} project${sources.length === 1 ? "" : "s"} queued for review.`,
      );
      $("#sources").value = "";
    } finally {
      button.disabled = false;
    }
  }),
);
$("#settings-form").addEventListener(
  "submit",
  safe(async (event) => {
    event.preventDefault();
    const form = event.target,
      values = Object.fromEntries(new FormData(form));
    for (const key of ["min_len", "max_len"]) values[key] = Number(values[key]);
    values.max_clips =
      values.max_clips === "" ? null : Number(values.max_clips);
    values.min_score =
      values.min_score === "" ? null : Number(values.min_score);
    values.preferred_len = (values.preferred_len || "").trim() || null;
    values.tighten = form.elements.tighten.checked;
    values.loudnorm = form.elements.loudnorm.checked;
    values.centers = [Number(values.center1), Number(values.center2)];
    delete values.center1;
    delete values.center2;
    values.llm = values.llm.trim() || null;
    values.vision_preset = values.vision_preset || "auto";
    values.ai_mode = values.ai_mode || "heuristic";
    values.ai_filter = values.ai_filter || "ollama";
    values.ai_companion = values.ai_companion || "claude";
    values.search = null;
    values.semantic = null;
    const mode = $("#search-mode").value;
    if (mode !== "auto") {
      if (!$("#query").value.trim())
        throw new Error("Enter a topic or keywords.");
      values[mode] = $("#query").value.trim();
    }
    await api(`/api/projects/${state.id}/settings`, values);
    notice(
      "Settings saved. Find clips again for search changes, or export with your new style.",
    );
  }),
);
$("#brand-form").addEventListener(
  "submit",
  safe(async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.target));
    const name = values.name;
    delete values.name;
    for (const key of ["font_size", "margin", "logo_width"])
      values[key] = Number(values[key]);
    values.logo = values.logo.trim() || null;
    await api("/api/brands", { name, preset: values });
    await config();
    $("#brand-select").value = name;
    notice("Brand preset saved. Save settings to apply it to this project.");
  }),
);
$("#candidates").addEventListener("input", (event) => {
  const selected = event.target.dataset.select;
  if (selected) {
    event.target.checked
      ? state.selected.add(Number(selected))
      : state.selected.delete(Number(selected));
    updateSelection();
  }
  const field = event.target.dataset.field;
  if (field) {
    const i = Number(event.target.closest("[data-index]").dataset.index);
    state.detail.candidates[i][field] =
      field === "hook" ? event.target.value : Number(event.target.value);
  }
});
let stopAt = null;
async function play(start, end = null) {
  const player = $("#source-player");
  stopAt = end;
  player.currentTime = start;
  await player.play();
}
async function watchCandidate(index) {
  const candidate = state.detail.candidates[index];
  if (state.detail.playable_source) {
    state.previewFile = null;
    await play(candidate.start, candidate.end);
    return;
  }
  if (state.busy || state.pendingPreview)
    throw new Error("Wait for the current job to finish.");
  const before = new Set(
    state.detail.files
      .filter((file) => file.kind === "previews" && file.name.endsWith(".mp4"))
      .map((file) => file.name),
  );
  state.pendingPreview = { index, before };
  state.previewFile = null;
  renderDetail();
  $("#player-hint").textContent =
    "Rendering this clip from its downloaded source section…";
  try {
    await saveCandidates(false);
    await api(`/api/projects/${state.id}/run`, {
      action: "render",
      preview: true,
      pick: String(index + 1),
    });
  } catch (error) {
    state.pendingPreview = null;
    renderDetail();
    throw error;
  }
  state.detail.busy = true;
  state.detail.project.status = "queued";
  state.detail.project.stage = "render";
  updateStatus(state.detail);
  notice("Rendering a 480p preview from a downloaded section…");
  await refreshProjects();
}
function loadPreview(file) {
  state.previewFile = file;
  const player = $("#source-player");
  player.src = file.url;
  player.hidden = false;
  $("#player-hint").hidden = true;
  player.currentTime = 0;
  player.play().catch(() => {});
}
$("#source-player").addEventListener("timeupdate", () => {
  if (stopAt !== null && $("#source-player").currentTime >= stopAt) {
    $("#source-player").pause();
    stopAt = null;
  }
  updateCaptionOverlay();
});
$("#source-player").addEventListener("seeked", () =>
  updateCaptionOverlay(true),
);
$("#source-player").addEventListener("loadedmetadata", () =>
  updateCaptionOverlay(true),
);
window.addEventListener("resize", () => {
  state.captionKey = "";
  updateCaptionOverlay(true);
});
$("#candidates").addEventListener(
  "click",
  safe(async (event) => {
    const button = event.target.closest("[data-play]");
    if (button) {
      await watchCandidate(Number(button.dataset.play));
    }
  }),
);
$("#transcript-words").addEventListener("input", (event) => {
  const field = event.target.dataset.wordField;
  if (field) {
    const i = Number(event.target.closest("[data-word]").dataset.word);
    state.words[i][field] =
      field === "word" ? event.target.value : Number(event.target.value);
  }
});
$("#transcript-words").addEventListener(
  "click",
  safe(async (event) => {
    const button = event.target.closest("[data-seek]");
    if (button) await play(state.words[Number(button.dataset.seek)].start);
  }),
);
$("#words-prev").addEventListener("click", () => {
  state.page--;
  renderWords();
});
$("#words-next").addEventListener("click", () => {
  state.page++;
  renderWords();
});
$("#candidates-prev").addEventListener("click", () => {
  state.candidatePage = Math.max(0, state.candidatePage - 1);
  renderDetail();
});
$("#candidates-next").addEventListener("click", () => {
  state.candidatePage++;
  renderDetail();
});
$("#select-all").addEventListener("click", () => {
  state.selected = new Set(state.detail.candidates.map((_, i) => i + 1));
  renderDetail();
});
$("#select-none").addEventListener("click", () => {
  state.selected.clear();
  renderDetail();
});
$("#show-clips").addEventListener("click", () => setTab("clips"));
$("#show-transcript").addEventListener("click", () => setTab("transcript"));
$("#show-captions").addEventListener("click", () => setTab("captions"));
$("#caption-form").addEventListener("input", () => syncCaption());
$("#caption-preset").addEventListener("change", (event) =>
  applyCaptionPreset(event.target.value),
);
$("#caption-presets").addEventListener("click", (event) => {
  const button = event.target.closest("[data-caption-preset]");
  if (button) applyCaptionPreset(button.dataset.captionPreset);
});
$("#caption-form").addEventListener(
  "submit",
  safe(async (event) => {
    event.preventDefault();
    const caption = captionFromForm();
    const style = $("#caption-preset").value;
    await api(`/api/projects/${state.id}/settings`, { caption, style });
    state.detail.project.options.caption = caption;
    state.detail.project.options.style = style;
    state.captionDraft = caption;
    markCaptionPreset(style);
    notice("Caption style saved for this project.");
  }),
);
$("#save-caption-preset").addEventListener(
  "click",
  safe(async () => {
    if (!state.detail) throw new Error("Select a project first.");
    const name = $("#caption-preset-name").value.trim();
    if (!name) throw new Error("Name the preset first.");
    await api("/api/brands", { name, preset: captionFromForm() });
    await config();
    $("#brand-select").value = name;
    notice(
      "Caption preset saved. Choose it under Brand preset, then Save settings.",
    );
  }),
);
$("#caption-preview").addEventListener(
  "click",
  safe(async () => {
    if (!state.detail?.transcript) throw new Error("Prepare the project first.");
    if (state.detail.playable_source === false)
      throw new Error(
        "Long sources have no full player. Use Watch on a clip to render and play its preview.",
      );
    const candidates = state.detail.candidates;
    const selected = [...state.selected].sort((a, b) => a - b);
    const clip = candidates[(selected[0] || 1) - 1] || candidates[0];
    setTab("captions");
    const start = clip ? Number(clip.start) : state.words[0]?.start || 0;
    await play(start, start + 5);
  }),
);
$("#prepare").addEventListener(
  "click",
  safe(() => run("prepare")),
);
$("#preview").addEventListener(
  "click",
  safe(() => run("render", true)),
);
$("#render").addEventListener(
  "click",
  safe(() => run("render")),
);
$("#save-candidates").addEventListener(
  "click",
  safe(() => saveCandidates()),
);
$("#save-transcript").addEventListener(
  "click",
  safe(async () => {
    await api(`/api/projects/${state.id}/transcript`, { words: state.words });
    notice("Caption edits saved. Export clips to apply them.");
  }),
);
let polling = false;
setInterval(async () => {
  if (polling) return;
  polling = true;
  try {
    await refreshProjects();
    if (state.id && state.busy) {
      const id = state.id,
        detail = await api(`/api/projects/${id}`);
      if (id !== state.id) return;
      const finished = !detail.busy;
      updateStatus(detail);
      if (finished) {
        const pending = state.pendingPreview;
        state.detail = detail;
        state.words = structuredClone(detail.transcript?.words || []);
        if (!pending) {
          state.selected = new Set(detail.candidates.map((_, i) => i + 1));
          state.candidatePage = 0;
        }
        let match = null;
        if (pending) {
          const previews = detail.files.filter(
            (file) => file.kind === "previews" && file.name.endsWith(".mp4"),
          );
          const fresh = previews.filter(
            (file) => !pending.before.has(file.name),
          );
          const prefix = `${String(pending.index + 1).padStart(3, "0")}-`;
          const failed =
            !!detail.project.error || (detail.render_errors || []).length > 0;
          match =
            fresh.find((file) => file.name.startsWith(prefix)) ||
            fresh[0] ||
            (!failed
              ? previews.find((file) => file.name.startsWith(prefix))
              : null) ||
            null;
          state.pendingPreview = null;
          state.previewFile = match;
        }
        renderDetail();
        if (pending) {
          if (match) {
            loadPreview(match);
            notice("Preview rendered from a downloaded source section.");
          } else {
            notice(
              detail.project.error ||
                "Preview finished, but no clip was produced.",
              true,
            );
          }
        } else {
          notice(
            detail.project.error || "Project ready for review.",
            !!detail.project.error,
          );
        }
      }
    }
    $("#connection").textContent = "● Local session";
  } catch (error) {
    $("#connection").textContent = "Connection lost · restart Studio";
  } finally {
    polling = false;
  }
}, 2000);
$("#outputs").addEventListener(
  "click",
  safe(async (event) => {
    const tabBtn = event.target.closest("[data-pub-tab]");
    if (tabBtn && state.detail) {
      outputPlatformState.set(tabBtn.dataset.stem, tabBtn.dataset.pubTab);
      renderOutputs(state.detail);
      return;
    }
    const copyBtn = event.target.closest("[data-copy-field]");
    if (copyBtn && state.detail) {
      const stem = copyBtn.dataset.stem;
      const field = copyBtn.dataset.copyField;
      const activePlat = outputPlatformState.get(stem) || "youtube_shorts";
      const kit = (state.detail.publish_kits || {})[stem];
      const text = kit?.platforms?.[activePlat]?.[field] || "";
      if (!text) throw new Error("Campo vazio para copiar.");
      const labels = { title: "Título", description: "Descrição", pinned_comment: "1º Comentário" };
      await copyToClipboard(text, labels[field] || "Texto");
      return;
    }
    const folderBtn = event.target.closest("[data-open-folder]");
    if (folderBtn && state.id) {
      await api(`/api/projects/${state.id}/open-folder`, {
        file: folderBtn.dataset.openFolder,
        kind: folderBtn.dataset.kind || "clips",
      });
      notice("Pasta aberta no explorador de arquivos.");
      return;
    }
    const cdBtn = event.target.closest("[data-cooldown], [data-cooldown-clear]");
    if (cdBtn && state.id && state.detail) {
      const clear = cdBtn.hasAttribute("data-cooldown-clear");
      const platform = clear ? cdBtn.dataset.cooldownClear : cdBtn.dataset.cooldown;
      if (!clear && !window.confirm(`Ativar Cool-Down de 48h em ${platform}? Novas postagens nessa rede ficam travadas.`)) return;
      await api("/api/risk/cooldown", clear ? { platform, clear: true } : { platform, hours: 48 });
      const status = await api("/api/risk/cooldown");
      state.detail.cooldowns = status.cooldowns || {};
      renderOutputs(state.detail);
      notice(clear ? `Cool-Down encerrado em ${platform}.` : `Cool-Down de 48h ativo em ${platform}.`);
      return;
    }
    const markBtn = event.target.closest("[data-mark-posted]");
    if (markBtn && state.id && state.detail) {
      const stem = markBtn.dataset.stem;
      const platform = markBtn.dataset.markPosted;
      const externalUrl = window.prompt(
        `Link do vídeo postado em ${platform} (opcional — pode deixar vazio e clicar OK):`,
        "",
      );
      if (externalUrl === null) return;
      const res = await api(`/api/projects/${state.id}/mark-posted`, {
        clip_stem: stem,
        platform,
        external_url: externalUrl.trim(),
      });
      state.detail.publications = state.detail.publications || {};
      state.detail.publications[stem] = state.detail.publications[stem] || {};
      state.detail.publications[stem][platform] = res.publication;
      renderOutputs(state.detail);
      notice(`Marcado como postado em ${platform} e salvo no banco!`);
    }
  }),
);
const bundleBtnEl = $("#export-daily-bundle");
if (bundleBtnEl) {
  bundleBtnEl.addEventListener(
    "click",
    safe(async () => {
      if (!state.id) return;
      const res = await api(`/api/projects/${state.id}/export-bundle`, {
        per_day: 3,
        open_folder: true,
      });
      notice(`Pacote do Dia gerado (${res.count} clipes) em: ${res.bundle_dir}`);
    }),
  );
}
safe(async () => {
  await config();
  await refreshProjects();
})();
