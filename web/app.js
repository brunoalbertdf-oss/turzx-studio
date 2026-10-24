// TURZX Studio: editor de telas
const $ = (s) => document.querySelector(s);
const el = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k === "class") e.className = v;
    else if (v !== undefined && v !== null && v !== false) e.setAttribute(k, v === true ? "" : v);
  }
  for (const k of kids.flat()) if (k != null) e.append(k.nodeType ? k : document.createTextNode(k));
  return e;
};

let cfg, catalog = {}, fonts = [], media = [], values = {};
let sel = 0;            // tela selecionada no editor
let selW = null;        // índice do widget selecionado
let scale = 1;
let liveIndex = 0;
let videoErrors = {};

const SIZES = { landscape: [800, 480], landscape_flipped: [800, 480], portrait: [480, 800], portrait_flipped: [480, 800] };
const SKIN_KEYS = { bg1: "Fundo 1", bg2: "Fundo 2", accent: "Destaque", accent2: "Destaque 2", text: "Texto",
  muted: "Texto suave", panel: "Painéis", warn: "Alerta" };
const HISTORY_KEYS = ["cpu_percent", "ram_percent", "gpu_percent", "gpu_temp", "cpu_temp", "fps", "net_down", "net_up"];

// ------------------------------------------------------------ tipos de widget

const TYPES = {
  text:   { label: "Texto", make: () => ({ text: "CPU {cpu_percent:.0f}%", w: 220, h: 40, size: 26, color: "$text", font: "segoeui.ttf", align: "left" }) },
  clock:  { label: "Relógio", type: "text", make: () => ({ text: "{time_s}", w: 300, h: 80, size: 64, color: "$text", font: "segoeuib.ttf", align: "center" }) },
  bar:    { label: "Barra", make: () => ({ value: "cpu_percent", w: 240, h: 14, color: "$accent", bg: "#ffffff22", min: 0, max: 100 }) },
  gauge:  { label: "Medidor", make: () => ({ value: "cpu_percent", w: 160, h: 160, color: "$accent", bg: "#ffffff1a", label: "CPU", min: 0, max: 100 }) },
  graph:  { label: "Gráfico", make: () => ({ value: "cpu_percent", w: 260, h: 80, color: "$accent", min: 0, max: 100 }) },
  panel:  { label: "Painel", make: () => ({ w: 260, h: 160, fill: "$panel", radius: 18 }) },
  media:  { label: "Imagem/GIF/Vídeo", make: () => ({ file: media[0] || "", w: 240, h: 240, fit: "cover", fps: 10 }) },
  weather_icon: { label: "Ícone do tempo", make: () => ({ w: 140, h: 140, color: "$text", color2: "$accent" }) },
  brand: { label: "CPU/GPU (logo + nome)", make: () => ({ device: "cpu", w: 340, h: 32, size: 18, color: "$text" }) },
  drives: { label: "HDs / SSDs", make: () => ({ w: 480, h: 120, max: 4, bar: "$accent", color: "$text", muted: "$muted" }) },
  deco: { label: "Decoração", make: () => ({ style: "rays", w: 300, h: 200, color: "#ffffff22", color2: "#ffffff0a" }) },
  forecast: { label: "Previsão", make: () => ({ w: 600, h: 150, days: 5, size: 18, color: "$text", muted: "$muted", icon_color: "$text", icon_color2: "$accent" }) },
};

const F = {
  text: (k, label) => ({ k, label, kind: "text" }),
  area: (k, label) => ({ k, label, kind: "area" }),
  num: (k, label, step = 1) => ({ k, label, kind: "num", step }),
  color: (k, label) => ({ k, label, kind: "color" }),
  bool: (k, label) => ({ k, label, kind: "bool" }),
  sel: (k, label, opts) => ({ k, label, kind: "select", opts }),
};
const ALIGN = [["left", "Esquerda"], ["center", "Centro"], ["right", "Direita"]];
const VALIGN = [["middle", "Meio"], ["top", "Topo"], ["bottom", "Base"]];
const FIT = [["cover", "Preencher (corta)"], ["contain", "Caber inteiro"], ["stretch", "Esticar"]];
const numericKeys = () => Object.keys(catalog).filter((k) => k !== "day" && (typeof values[k] === "number" || ["cpu_temp", "cpu_power", "fps", "frametime"].includes(k))).map((k) => [k, `${k} — ${catalog[k]}`]);
const fontOpts = () => fonts.map((f) => [f, f]);
const mediaOpts = () => [["", "(nenhum)"], ...media.map((m) => [m, m])];

const FIELDS = {
  text: () => [F.area("text", "Texto (use {variável})"), F.sel("font", "Fonte", fontOpts()), F.num("size", "Tamanho"),
    F.color("color", "Cor"), F.sel("align", "Alinhamento", ALIGN), F.sel("valign", "Vertical", VALIGN),
    F.bool("shadow", "Sombra"), F.color("shadow_color", "Cor da sombra")],
  panel: () => [F.color("fill", "Preenchimento"), F.color("outline", "Contorno"), F.num("outline_width", "Espessura do contorno"),
    F.num("radius", "Arredondamento")],
  bar: () => [F.sel("value", "Valor", numericKeys()), F.num("min", "Mínimo"), F.num("max", "Máximo"), F.color("color", "Cor"),
    F.color("bg", "Fundo"), F.num("radius", "Arredondamento"), F.bool("vertical", "Vertical"),
    F.num("warn_at", "Alerta a partir de (%)"), F.color("warn_color", "Cor de alerta")],
  gauge: () => [F.sel("value", "Valor", numericKeys()), F.num("min", "Mínimo"), F.num("max", "Máximo"), F.color("color", "Cor"),
    F.color("bg", "Fundo do arco"), F.num("thickness", "Espessura"), F.text("label", "Rótulo"), F.text("unit", "Unidade"),
    F.text("text", "Texto central (opcional)"), F.bool("show_value", "Mostrar valor"), F.sel("font", "Fonte", fontOpts()),
    F.num("size", "Tamanho do texto"), F.color("text_color", "Cor do texto"), F.color("label_color", "Cor do rótulo"),
    F.num("warn_at", "Alerta a partir de (%)"), F.color("warn_color", "Cor de alerta")],
  graph: () => [F.sel("value", "Valor (histórico de 2 min)", HISTORY_KEYS.map((k) => [k, `${k} — ${catalog[k] || ""}`])),
    F.num("min", "Mínimo"), F.text("max", "Máximo (número ou auto)"), F.color("color", "Cor"), F.color("bg", "Fundo"),
    F.num("thickness", "Espessura da linha"), F.bool("fill", "Preencher área"), F.num("radius", "Arredondamento")],
  media: () => [F.sel("file", "Arquivo", mediaOpts()), F.sel("fit", "Ajuste", FIT), F.num("fps", "FPS do vídeo"),
    F.num("speed", "Velocidade do GIF", 0.1), F.num("radius", "Arredondamento"), F.num("opacity", "Opacidade (0–1)", 0.05)],
  weather_icon: () => [F.color("color", "Cor da nuvem"), F.color("color2", "Cor do sol/chuva")],
  brand: () => [F.sel("device", "Peça", [["cpu", "CPU"], ["gpu", "GPU"]]),
    F.sel("style", "Estilo do logo", [["badge", "Selo colorido"], ["text", "Só o nome da marca"]]),
    F.bool("show_name", "Mostrar o modelo ao lado"), F.bool("full_name", "Nome completo do modelo"),
    F.sel("font", "Fonte", fontOpts()), F.num("size", "Tamanho"), F.color("color", "Cor do modelo")],
  drives: () => [F.text("letters", "Só estas unidades (ex.: C,D; vazio = todas)"), F.num("max", "Máximo de unidades"),
    F.bool("show_label", "Mostrar nome do volume"), F.sel("font", "Fonte", fontOpts()), F.num("size", "Tamanho"),
    F.color("color", "Cor do texto"), F.color("muted", "Cor do espaço livre"), F.color("bar", "Cor da barra"),
    F.color("bg", "Fundo da barra"), F.num("warn_at", "Alerta a partir de (%)"), F.color("warn_color", "Cor de alerta")],
  deco: () => [F.sel("style", "Desenho", [["rays", "Raios de energia"], ["glow", "Brilho / aura"], ["orb", "Esfera com estrelas"],
      ["stars", "Estrelas"], ["spiral", "Redemoinho"], ["leaf", "Emblema de folha"], ["grid", "Grade HUD"],
      ["scanlines", "Linhas de varredura"], ["hex", "Colmeia"], ["crosshair", "Mira"], ["stripes", "Faixas de corrida"],
      ["speedlines", "Linhas de velocidade"], ["checker", "Quadriculado"], ["skyline", "Cidade"], ["camo", "Camuflagem"],
      ["chevrons", "Divisas"]]),
    F.color("color", "Cor 1"), F.color("color2", "Cor 2"), F.num("count", "Quantidade"), F.num("step", "Espaçamento"),
    F.num("thickness", "Espessura"), F.num("seed", "Variação (número)"), F.num("cx", "Centro X (0–1)", 0.05),
    F.num("cy", "Centro Y (0–1)", 0.05)],
  forecast: () => [F.num("days", "Dias (1–5)"), F.sel("font", "Fonte", fontOpts()), F.num("size", "Tamanho"),
    F.color("color", "Cor do dia"), F.color("muted", "Cor das temperaturas"), F.color("icon_color", "Cor da nuvem"),
    F.color("icon_color2", "Cor do sol/chuva")],
};
const TYPE_LABEL = { brand: "CPU/GPU", drives: "HDs", deco: "Decoração", text: "Texto", bar: "Barra", gauge: "Medidor", graph: "Gráfico", panel: "Painel", media: "Mídia",
  weather_icon: "Ícone do tempo", forecast: "Previsão" };

// ------------------------------------------------------------ API

async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : { method: "POST", body: typeof body === "string" || body instanceof Blob ? body : JSON.stringify(body) });
  return r.json();
}

let saveTimer;
const undoStack = [], redoStack = [];
let lastSaved = null;

function restore(json) {
  cfg = JSON.parse(json); lastSaved = json;
  sel = Math.min(sel, cfg.screens.length - 1);
  if (selW != null && selW >= (screen()?.widgets.length || 0)) selW = null;
  api("/api/config", cfg).then(refreshPreview);
  renderSkins(); renderScreens(); renderAll();
}

function save(refreshProps = false) {
  const json = JSON.stringify(cfg);
  if (lastSaved && json !== lastSaved) {
    undoStack.push(lastSaved); if (undoStack.length > 100) undoStack.shift();
    redoStack.length = 0;
  }
  lastSaved = json;
  $("#saveState").textContent = "salvando…";
  clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {
    const r = await api("/api/config", cfg);
    $("#saveState").textContent = r.ok ? "salvo ✓" : "erro ao salvar";
    refreshPreview();
  }, 350);
  renderOverlay();
  renderLayers();
  if (refreshProps) renderProps();
}

// ------------------------------------------------------------ helpers

const screen = () => cfg.screens[sel];
const widget = () => (selW != null ? screen()?.widgets[selW] : null);
const logicalSize = () => SIZES[cfg.settings.orientation] || SIZES.landscape;
const skinOf = (s) => cfg.skins[(s && s.skin) || cfg.settings.skin] || Object.values(cfg.skins)[0];

function resolveHex(v, s) {
  if (typeof v === "string" && v.startsWith("$")) v = skinOf(s)[v.slice(1)] || "#ffffff";
  return /^#[0-9a-f]{6}/i.test(v || "") ? v.slice(0, 7) : "#ffffff";
}

function colorInput(value, onChange, s) {
  const txt = el("input", { value: value || "", list: "skinVars", placeholder: "#rrggbb, #rrggbbaa ou $accent" });
  const pick = el("input", { type: "color", value: resolveHex(value, s) });
  txt.addEventListener("change", () => { pick.value = resolveHex(txt.value, s); onChange(txt.value); });
  pick.addEventListener("input", () => {
    const alpha = /^#[0-9a-f]{8}$/i.test(txt.value) ? txt.value.slice(7) : "";
    txt.value = pick.value + alpha; onChange(txt.value);
  });
  return el("div", { class: "colorRow" }, txt, pick);
}

function fieldEditor(obj, f, onChange, s) {
  const set = (v) => { if (v === "" || v === undefined) delete obj[f.k]; else obj[f.k] = v; onChange(); };
  let input;
  if (f.kind === "bool") {
    const defTrue = f.k === "show_value" || f.k === "fill";
    input = el("input", { type: "checkbox" });
    input.checked = obj[f.k] ?? defTrue;
    input.addEventListener("change", () => { obj[f.k] = input.checked; onChange(); });
    return el("label", { class: "field check" }, input, f.label);
  }
  if (f.kind === "color") input = colorInput(obj[f.k], (v) => set(v), s);
  else if (f.kind === "select") {
    input = el("select", {}, ...f.opts.map(([v, l]) => el("option", { value: v }, l)));
    if (obj[f.k] !== undefined && !f.opts.some(([v]) => v === obj[f.k])) input.prepend(el("option", { value: obj[f.k] }, obj[f.k]));
    if (obj[f.k] === undefined && !f.opts.some(([v]) => v === "")) input.prepend(el("option", { value: "" }, "(padrão)"));
    input.value = obj[f.k] ?? "";
    input.addEventListener("change", () => set(input.value));
  } else if (f.kind === "area") {
    input = el("textarea", {}, obj[f.k] ?? "");
    input.addEventListener("input", () => set(input.value));
    const chips = el("div", { class: "chips" }, ...["time_s", "time", "date", "weekday", "cpu_percent:.0f", "gpu_percent:.0f",
      "gpu_temp:.0f", "cpu_temp", "ram_percent:.0f", "fps", "cpu_name", "gpu_name", "disk_c_free", "weather_temp", "weather_desc"].map((v) =>
      el("button", { onclick: () => { insertAtCursor(input, `{${v}}`); set(input.value); } }, v)));
    return el("div", { class: "field" }, el("span", {}, f.label), input, chips);
  } else {
    input = el("input", { type: f.kind === "num" ? "number" : "text", step: f.step, value: obj[f.k] ?? "" });
    input.addEventListener("input", () => set(f.kind === "num" && input.value !== "" ? Number(input.value) : input.value));
  }
  return el("div", { class: "field" }, el("span", {}, f.label), input);
}

function insertAtCursor(ta, text) {
  const a = ta.selectionStart ?? ta.value.length, b = ta.selectionEnd ?? a;
  ta.value = ta.value.slice(0, a) + text + ta.value.slice(b);
  ta.focus(); ta.selectionStart = ta.selectionEnd = a + text.length;
}

// ------------------------------------------------------------ telas (lista à esquerda)

function renderScreens() {
  const ul = $("#screenList"); ul.innerHTML = "";
  cfg.screens.forEach((s, i) => {
    const chk = el("input", { type: "checkbox", title: "Incluir no carrossel" });
    chk.checked = s.enabled !== false;
    chk.addEventListener("click", (e) => e.stopPropagation());
    chk.addEventListener("change", () => { s.enabled = chk.checked; save(); renderScreens(); });
    ul.append(el("li", { class: i === sel ? "active" : "", onclick: () => selectScreen(i) },
      chk, el("span", { class: "name" }, (s.kind === "device_video" ? "🎬 " : "") + (s.name || `Tela ${i + 1}`)),
      i === liveIndex ? el("span", { class: "live", title: "Na tela física agora" }, "● ao vivo") : null,
      el("span", { class: "tag" }, `${s.duration || 15}s`)));
  });
}

function selectScreen(i) {
  sel = Math.max(0, Math.min(i, cfg.screens.length - 1)); selW = null;
  renderScreens(); renderAll();
}

function renderLayers() {
  const ul = $("#layerList"); ul.innerHTML = "";
  const s = screen(); if (!s) return;
  [...s.widgets.keys()].reverse().forEach((i) => {
    const w = s.widgets[i];
    const desc = w.type === "text" ? (w.text || "").slice(0, 22) : w.type === "media" ? w.file : w.value || "";
    ul.append(el("li", { class: i === selW ? "active" : "", onclick: () => { selW = i; renderOverlay(); renderLayers(); renderProps(); } },
      el("span", { class: "name" }, `${TYPE_LABEL[w.type] || w.type}  `, el("span", { class: "tag" }, desc)),
      w.hidden ? el("span", { class: "tag" }, "oculto") : null));
  });
}

// ------------------------------------------------------------ palco (prévia + caixas arrastáveis)

function fitStage() {
  const [w, h] = logicalSize();
  const wrap = $("#stageWrap").getBoundingClientRect();
  scale = Math.max(0.2, Math.min(1.25, (wrap.width - 20) / w, (wrap.height - 20) / h));
  const holder = $("#stageHolder");
  holder.style.width = `${w * scale}px`; holder.style.height = `${h * scale}px`;
  const st = $("#stage");
  st.style.width = `${w}px`; st.style.height = `${h}px`;
  st.style.transform = `scale(${scale})`;
}

function renderOverlay() {
  const ov = $("#overlay"); ov.innerHTML = "";
  const s = screen(); if (!s) return;
  s.widgets.forEach((w, i) => {
    if (w.hidden) return;
    const box = el("div", { class: "wbox" + (i === selW ? " sel" : "") },
      el("div", { class: "lbl" }, `${TYPE_LABEL[w.type]} · ${w.x},${w.y} · ${w.w}×${w.h}`), el("div", { class: "handle" }));
    Object.assign(box.style, { left: `${w.x}px`, top: `${w.y}px`, width: `${w.w}px`, height: `${w.h}px` });
    box.addEventListener("pointerdown", (e) => startDrag(e, i, e.target.classList.contains("handle")));
    ov.append(box);
  });
}

function startDrag(e, i, resize) {
  e.preventDefault(); e.stopPropagation();
  const w = screen().widgets[i];
  if (selW !== i) { selW = i; renderProps(); renderLayers(); }
  const sx = e.clientX, sy = e.clientY, o = { ...w };
  const [W, H] = logicalSize();
  const snap = (v) => ($("#showGrid").checked ? Math.round(v / 10) * 10 : Math.round(v));
  const move = (ev) => {
    const dx = (ev.clientX - sx) / scale, dy = (ev.clientY - sy) / scale;
    if (resize) { w.w = Math.max(8, snap(o.w + dx)); w.h = Math.max(8, snap(o.h + dy)); }
    else { w.x = Math.min(W - 8, Math.max(-w.w + 8, snap(o.x + dx))); w.y = Math.min(H - 8, Math.max(-w.h + 8, snap(o.y + dy))); }
    renderOverlay();
  };
  const up = () => {
    window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up);
    if (w.x !== o.x || w.y !== o.y || w.w !== o.w || w.h !== o.h) save(true); else renderOverlay();
  };
  window.addEventListener("pointermove", move); window.addEventListener("pointerup", up);
  renderOverlay();
}

$("#overlay").addEventListener("pointerdown", (e) => {
  if (e.target.id === "overlay") { selW = null; renderOverlay(); renderLayers(); renderProps(); }
});

let previewBusy = false;
function refreshPreview() {
  if (previewBusy || document.hidden) return;
  previewBusy = true;
  const img = new Image();
  img.onload = img.onerror = () => { previewBusy = false; if (img.naturalWidth) $("#preview").src = img.src; };
  img.src = ($("#liveView").checked ? "/api/live.png" : `/api/preview/${sel}.png`) + `?t=${Date.now()}`;
}

// ------------------------------------------------------------ propriedades (direita)

function renderProps() {
  const p = $("#props"); p.innerHTML = "";
  const s = screen(); if (!s) return;
  const w = widget();
  if (!w) {
    $("#propTitle").textContent = "Tela";
    const bg = (s.background ||= { type: "gradient", color1: "$bg1", color2: "$bg2" });
    const skinOpts = [["", `(padrão: ${cfg.settings.skin})`], ...Object.keys(cfg.skins).map((k) => [k, k])];
    const fields = [F.text("name", "Nome"), F.num("duration", "Duração no carrossel (s)"),
      F.sel("kind", "Tipo", [["", "Painel (widgets)"], ["device_video", "Vídeo fluido na tela (24 qps)"]])];
    if (s.kind !== "device_video") fields.push(F.sel("skin", "Skin desta tela", skinOpts));
    fields.forEach((f) => p.append(fieldEditor(s, f, () => { save(f.k === "kind"); renderScreens(); }, s)));
    if (s.kind === "device_video") {
      const vids = media.filter((m) => /\.(gif|webp|mp4|mkv|webm|mov|avi)$/i.test(m));
      p.append(fieldEditor(s, F.sel("file", "GIF ou vídeo", [["", "(escolha)"], ...vids.map((m) => [m, m])]), () => save(), s));
      p.append(el("p", { class: "muted" }, "A tela grava o vídeo na memória dela e toca sozinha, bem fluido. " +
        "Enquanto ele toca, as informações do PC não aparecem (a tela não sobrepõe imagens ao vídeo). " +
        "A memória da tela é pequena (~10 MB): veja o espaço na aba Mídia."));
      const err = videoErrors[sel];
      if (err) p.append(el("p", { class: "warn" }, `Último erro: ${err}`));
      return;
    }
    p.append(el("h4", {}, "Fundo"));
    const bgFields = [F.sel("type", "Tipo", [["gradient", "Degradê"], ["color", "Cor sólida"], ["media", "Imagem/GIF/Vídeo"]]),
      F.color("color1", "Cor 1")];
    if (bg.type !== "color" && bg.type !== "media") bgFields.push(F.color("color2", "Cor 2"),
      F.sel("direction", "Direção", [["vertical", "Vertical"], ["horizontal", "Horizontal"], ["diagonal", "Diagonal"]]));
    if (bg.type === "media") bgFields.push(F.sel("file", "Arquivo", mediaOpts()), F.sel("fit", "Ajuste", FIT), F.num("fps", "FPS do vídeo"));
    bgFields.forEach((f) => p.append(fieldEditor(bg, f, () => save(f.k === "type"), s)));
    if (bg.type === "media") p.append(el("p", { class: "muted" }, "Vídeo de fundo em tela cheia é lento (~1–2 qps). Prefira imagem ou GIF pequeno."));
    return;
  }
  $("#propTitle").textContent = TYPE_LABEL[w.type] || w.type;
  const xy = el("div", { class: "xywh" });
  for (const k of ["x", "y", "w", "h"]) {
    const inp = el("input", { type: "number", value: w[k], title: k });
    inp.addEventListener("input", () => { w[k] = Number(inp.value) || 0; save(); });
    xy.append(inp);
  }
  p.append(el("div", { class: "field" }, el("span", {}, "Posição e tamanho (x, y, largura, altura)"), xy));
  (FIELDS[w.type] || (() => []))().forEach((f) => p.append(fieldEditor(w, f, () => save(), s)));
  if (w.type === "media" && /\.(gif|webp|mp4|mkv|webm|mov|avi)$/i.test(w.file || "")) {
    p.append(el("p", { class: "muted" }, `Estimativa na tela: ~${estFps(w.w, w.h)} qps nesta área ` +
      "(a tela recebe ~780 KB/s; áreas menores ficam mais fluidas)."));
  }
  p.append(fieldEditor(w, F.bool("hidden", "Ocultar"), () => save(), s));
  p.append(el("div", { class: "row" },
    el("button", { onclick: () => moveLayer(1) }, "Trazer p/ frente"),
    el("button", { onclick: () => moveLayer(-1) }, "Enviar p/ trás")));
  p.append(el("div", { class: "row" },
    el("button", { onclick: dupWidget }, "Duplicar"),
    el("button", { class: "danger", onclick: delWidget }, "Excluir")));
}

const estFps = (w, h) => Math.max(0.1, Math.min(10, 780000 / (w * h * 3))).toFixed(1);

function moveLayer(d) {
  const ws = screen().widgets, j = selW + d;
  if (j < 0 || j >= ws.length) return;
  [ws[selW], ws[j]] = [ws[j], ws[selW]]; selW = j; save(true);
}
function dupWidget() {
  const w = widget(); if (!w) return;
  const c = structuredClone(w); c.x += 10; c.y += 10;
  screen().widgets.push(c); selW = screen().widgets.length - 1; save(true);
}
function delWidget() {
  if (selW == null) return;
  screen().widgets.splice(selW, 1); selW = null; save(true);
}

function addWidget(key) {
  const t = TYPES[key], [W, H] = logicalSize();
  const w = { type: t.type || key, ...t.make() };
  w.x = Math.round((W - w.w) / 2); w.y = Math.round((H - w.h) / 2);
  screen().widgets.push(w); selW = screen().widgets.length - 1; save(true);
}

// ------------------------------------------------------------ skins

function renderSkins() {
  const names = Object.keys(cfg.skins);
  for (const id of ["#skinSelect", "#globalSkin"]) {
    const s = $(id), cur = id === "#globalSkin" ? cfg.settings.skin : (s.value || cfg.settings.skin);
    s.innerHTML = ""; names.forEach((n) => s.append(el("option", { value: n }, n)));
    s.value = names.includes(cur) ? cur : names[0];
  }
  const name = $("#skinSelect").value, skin = cfg.skins[name], box = $("#skinColors");
  box.innerHTML = "";
  for (const [k, label] of Object.entries(SKIN_KEYS)) {
    const row = colorInput(skin[k], (v) => { skin[k] = v; save(); }, null);
    box.append(el("div", { class: "field" }, el("span", {}, label), ...row.children));
  }
  for (const [k, label] of [["font_title", "Fonte títulos"], ["font_num", "Fonte números"]]) {
    const sel = el("select", {}, ...fonts.map((f) => el("option", { value: f }, f)));
    sel.value = skin[k] || "segoeuib.ttf";
    sel.addEventListener("change", () => { skin[k] = sel.value; save(); });
    box.append(el("div", { class: "field" }, el("span", {}, label), sel));
  }
  if ((skin.decor || []).length) {
    const chk = el("input", { type: "checkbox" }); chk.checked = !skin.decor_off;
    chk.addEventListener("change", () => { skin.decor_off = !chk.checked; save(); });
    box.append(el("label", { class: "check" }, chk, " Mostrar o fundo decorado da skin"));
  }
  $("#skinVars").innerHTML = "";
  Object.keys(SKIN_KEYS).forEach((k) => $("#skinVars").append(el("option", { value: `$${k}` })));
}

$("#skinSelect").addEventListener("change", renderSkins);
$("#globalSkin").addEventListener("change", (e) => {
  cfg.settings.skin = e.target.value; $("#skinSelect").value = e.target.value; renderSkins(); save(true);
  if ($("#tab-skins").classList.contains("active")) loadSkinGallery();
});
$("#newSkin").addEventListener("click", () => {
  const n = prompt("Nome da nova skin (copia a atual):"); if (!n || cfg.skins[n]) return;
  cfg.skins[n] = structuredClone(cfg.skins[$("#skinSelect").value]);
  renderSkins(); $("#skinSelect").value = n; renderSkins(); save();
});
$("#renameSkin").addEventListener("click", () => {
  const old = $("#skinSelect").value, n = prompt("Novo nome:", old); if (!n || n === old || cfg.skins[n]) return;
  cfg.skins[n] = cfg.skins[old]; delete cfg.skins[old];
  if (cfg.settings.skin === old) cfg.settings.skin = n;
  cfg.screens.forEach((s) => { if (s.skin === old) s.skin = n; });
  renderSkins(); $("#skinSelect").value = n; renderSkins(); save(true);
});
$("#delSkin").addEventListener("click", () => {
  const n = $("#skinSelect").value;
  if (Object.keys(cfg.skins).length < 2 || !confirm(`Excluir a skin "${n}"?`)) return;
  delete cfg.skins[n];
  const first = Object.keys(cfg.skins)[0];
  if (cfg.settings.skin === n) cfg.settings.skin = first;
  cfg.screens.forEach((s) => { if (s.skin === n) delete s.skin; });
  $("#skinSelect").value = first; renderSkins(); save(true);
});

// ------------------------------------------------------------ mídia

function renderMedia() {
  const ul = $("#mediaList"); ul.innerHTML = "";
  media.forEach((m) => {
    const isVid = /\.(mp4|mkv|webm|mov|avi)$/i.test(m);
    ul.append(el("li", {}, isVid ? el("span", { class: "tag" }, "🎬") : el("img", { src: `/media/${encodeURIComponent(m)}` }),
      el("span", { class: "name", title: m }, m),
      el("button", { class: "danger", onclick: async () => {
        if (!confirm(`Excluir ${m}?`)) return;
        media = (await api(`/api/media/delete?name=${encodeURIComponent(m)}`, "")).media; renderMedia(); renderProps();
      } }, "✕")));
  });
}
$("#refreshDevice").addEventListener("click", loadDevice);
$("#upload").addEventListener("change", async (e) => {
  for (const f of e.target.files) {
    const r = await fetch(`/api/upload?name=${encodeURIComponent(f.name)}`, { method: "POST", body: f }).then((r) => r.json());
    if (r.error) alert(`${f.name}: ${r.error}`); else media = r.media;
  }
  e.target.value = ""; renderMedia(); renderProps();
});

// ------------------------------------------------------------ galeria de skins e telas prontas

async function loadSkinGallery() {
  const box = $("#skinGallery"); box.innerHTML = "";
  const packs = await fetch("/api/skins").then((r) => r.json());
  const info = Object.fromEntries(packs.map((p) => [p.name, p]));
  const names = [...new Set([...packs.map((p) => p.name), ...Object.keys(cfg.skins)])];
  const screenIdx = Math.max(0, cfg.screens.filter((s) => s.kind !== "device_video").indexOf(screen()));
  names.forEach((n) => {
    const p = info[n] || { name: n, description: "Skin personalizada." };
    const active = cfg.settings.skin === n;
    box.append(el("div", { class: "theme" + (active ? " active" : "") },
      el("img", { src: `/api/skin_preview.png?name=${encodeURIComponent(n)}&screen=${screenIdx}`, alt: n, loading: "lazy" }),
      el("b", {}, n + (active ? "  ✓ em uso" : "")),
      p.inspired ? el("span", { class: "tag" }, `inspirada em ${p.inspired}`) : null,
      el("p", { class: "muted" }, p.description),
      active ? null : el("button", { onclick: async () => {
        const before = JSON.stringify(cfg);
        const r = await fetch(`/api/skin/use?name=${encodeURIComponent(n)}`, { method: "POST" }).then((x) => x.json());
        if (r.error) return alert(r.error);
        undoStack.push(before); redoStack.length = 0;
        cfg = r.config; lastSaved = JSON.stringify(cfg);
        renderSkins(); renderAll(); loadSkinGallery();
      } }, "Usar esta skin")));
  });
}

async function initLayouts() {
  const list = await fetch("/api/layouts").then((r) => r.json());
  list.forEach((l) => $("#addLayout").append(el("button", { title: l.description, onclick: async () => {
    const before = JSON.stringify(cfg);
    const r = await fetch(`/api/layout/add?id=${l.id}`, { method: "POST" }).then((x) => x.json());
    if (r.error) return alert(r.error);
    undoStack.push(before); redoStack.length = 0;
    cfg = r.config; lastSaved = JSON.stringify(cfg);
    selectScreen(r.index);
  } }, "+ " + l.name)));
}

// ------------------------------------------------------------ memória da tela

async function loadDevice() {
  const box = $("#deviceInfo"); box.textContent = "Consultando a tela…";
  const r = await fetch("/api/device").then((x) => x.json());
  renderDevice(r);
}

function renderDevice(r) {
  const box = $("#deviceInfo"); box.innerHTML = "";
  if (r.error) { box.append(el("p", { class: "warn" }, r.error)); return; }
  const pct = r.total_kb ? Math.round((r.used_kb / r.total_kb) * 100) : 0;
  box.append(el("p", {}, `Livre: ${(r.free_kb / 1024).toFixed(1)} MB de ${(r.total_kb / 1024).toFixed(1)} MB (${pct}% usado)`));
  const bar = el("div", { class: "meter" }, el("div", { style: `width:${pct}%` }));
  box.append(bar);
  const ul = el("ul", { class: "list" });
  r.files.forEach((f) => {
    const ours = r.ours.includes(f);
    ul.append(el("li", {}, el("span", { class: "name", title: f }, f),
      el("span", { class: "tag" }, `${((r.sizes?.[f] || 0) / 1048576).toFixed(1)} MB · ${ours ? "do app" : "da tela"}`),
      el("button", { class: "danger", title: "Apagar da memória da tela", onclick: async () => {
        const msg = ours ? `Apagar ${f} da memória da tela? (o app envia de novo se precisar)`
          : `${f} não foi enviado por este app (pode ser um vídeo de fábrica). Apagar mesmo assim? Não dá para desfazer.`;
        if (!confirm(msg)) return;
        renderDevice(await fetch(`/api/device/delete?name=${encodeURIComponent(f)}`, { method: "POST" }).then((x) => x.json()));
      } }, "✕")));
  });
  box.append(ul);
}

// ------------------------------------------------------------ cabeçalho e ajustes

function bindSettings() {
  const st = cfg.settings;
  const bind = (id, key, conv = (v) => v, ev = "change") => {
    const e = $(id);
    if (e.type === "checkbox") e.checked = !!st[key]; else e.value = st[key] ?? "";
    e.addEventListener(ev, () => { st[key] = e.type === "checkbox" ? e.checked : conv(e.value); save(); if (key === "orientation") { fitStage(); renderOverlay(); } });
  };
  bind("#brightness", "brightness", Number, "input");
  bind("#orientation", "orientation");
  bind("#city", "city");
  bind("#carousel", "carousel");
  bind("#maxFps", "max_fps", Number);
  bind("#transition", "transition");
  bind("#autostart", "autostart");
  bind("#port", "port");
  bind("#ffmpeg", "ffmpeg");
  bind("#lhm", "lhm_url");
  const bv = () => ($("#brightnessVal").textContent = `${st.brightness}%`);
  $("#brightness").addEventListener("input", bv); bv();
}

function renderCatalog() {
  const t = $("#catalog"); t.innerHTML = "";
  for (const [k, d] of Object.entries(catalog)) {
    const v = values[k];
    t.append(el("tr", {}, el("td", { title: "Clique para copiar", onclick: () => navigator.clipboard?.writeText(`{${k}}`) }, `{${k}}`),
      el("td", {}, d), el("td", {}, v === undefined ? "" : String(v))));
  }
}

$("#addScreen").addEventListener("click", () => {
  cfg.screens.push({ name: `Tela ${cfg.screens.length + 1}`, duration: 15, enabled: true,
    background: { type: "gradient", color1: "$bg1", color2: "$bg2", direction: "diagonal" }, widgets: [] });
  selectScreen(cfg.screens.length - 1); save();
});
$("#dupScreen").addEventListener("click", () => {
  const c = structuredClone(screen()); c.name += " (cópia)";
  cfg.screens.splice(sel + 1, 0, c); selectScreen(sel + 1); save();
});
$("#delScreen").addEventListener("click", () => {
  if (cfg.screens.length < 2 || !confirm(`Excluir a tela "${screen().name}"?`)) return;
  cfg.screens.splice(sel, 1); selectScreen(Math.max(0, sel - 1)); save();
});
const moveScreen = (d) => {
  const j = sel + d; if (j < 0 || j >= cfg.screens.length) return;
  [cfg.screens[sel], cfg.screens[j]] = [cfg.screens[j], cfg.screens[sel]]; selectScreen(j); save();
};
$("#upScreen").addEventListener("click", () => moveScreen(-1));
$("#downScreen").addEventListener("click", () => moveScreen(1));
$("#pinScreen").addEventListener("click", async () => {
  const pinned = $("#pinScreen").dataset.pinned === "1";
  await api("/api/control", pinned ? { action: "unpin" } : { action: "pin", index: sel });
  pollStatus();
});
$("#prevScreen").addEventListener("click", () => api("/api/control", { action: "prev" }).then(pollStatus));
$("#nextScreen").addEventListener("click", () => api("/api/control", { action: "next" }).then(pollStatus));
$("#liveView").addEventListener("change", (e) => { $("#overlay").classList.toggle("live", e.target.checked); refreshPreview(); });
$("#showGrid").addEventListener("change", (e) => $("#overlay").classList.toggle("grid", e.target.checked));

document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll(".tabs button, .tab").forEach((x) => x.classList.remove("active"));
  b.classList.add("active"); $(`#tab-${b.dataset.tab}`).classList.add("active");
  if (b.dataset.tab === "settings") { renderCatalog(); loadLogos(); }
  if (b.dataset.tab === "media") loadDevice();
  if (b.dataset.tab === "skins") loadSkinGallery();
}));

document.addEventListener("keydown", (e) => {
  if (/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) return;
  if (e.ctrlKey && e.key.toLowerCase() === "z" && undoStack.length) {
    e.preventDefault(); redoStack.push(JSON.stringify(cfg)); restore(undoStack.pop()); return;
  }
  if (e.ctrlKey && e.key.toLowerCase() === "y" && redoStack.length) {
    e.preventDefault(); undoStack.push(JSON.stringify(cfg)); restore(redoStack.pop()); return;
  }
  const w = widget(); if (!w) return;
  const step = e.shiftKey ? 10 : 1;
  const moves = { ArrowLeft: ["x", -step], ArrowRight: ["x", step], ArrowUp: ["y", -step], ArrowDown: ["y", step] };
  if (moves[e.key]) { e.preventDefault(); const [k, d] = moves[e.key]; w[k] += d; save(true); }
  else if (e.key === "Delete") delWidget();
  else if (e.key.toLowerCase() === "d" && e.ctrlKey) { e.preventDefault(); dupWidget(); }
  else if (e.key === "Escape") { selW = null; renderOverlay(); renderLayers(); renderProps(); }
});

// ------------------------------------------------------------ logos dos fabricantes

async function loadLogos() {
  const st = await fetch("/api/logos").then((r) => r.json());
  const box = $("#logos"); box.innerHTML = "";
  for (const [vendor, has] of Object.entries(st)) {
    const slot = (variant, label, bg) => {
      const file = `${vendor.toLowerCase()}${variant === "white" ? "-white" : ""}.png`;
      const input = el("input", { type: "file", accept: "image/png,image/*" });
      input.addEventListener("change", async () => {
        const f = input.files[0]; if (!f) return;
        const r = await fetch(`/api/logo?vendor=${vendor}&variant=${variant}`, { method: "POST", body: f }).then((x) => x.json());
        if (r.error) alert(r.error);
        loadLogos(); refreshPreview();
      });
      const exists = has[variant];
      return el("div", { class: "slot" },
        el("div", { class: "pv", style: `background:var(${bg})` },
          exists ? el("img", { src: `/logos/${file}?t=${Date.now()}`, alt: file }) : el("span", { class: "muted" }, "—")),
        el("div", {}, label),
        el("label", {}, exists ? "trocar" : "enviar", input),
        exists ? el("button", { class: "danger", title: "Remover", onclick: async () => {
          await fetch(`/api/logo/delete?vendor=${vendor}&variant=${variant}`, { method: "POST" }); loadLogos(); refreshPreview();
        } }, "✕") : null);
    };
    box.append(el("div", { class: "vendor" }, el("b", {}, vendor),
      el("div", { class: "slots" }, slot("white", "Fundo escuro (branca)", "--logo-dark"), slot("normal", "Fundo claro (preta/colorida)", "--logo-light"))));
  }
}

// ------------------------------------------------------------ fontes de dados (Afterburner / RivaTuner)

let bannerDismissed = false;
try { bannerDismissed = localStorage.getItem("abBanner") === "off"; } catch {}
$("#abDismiss").addEventListener("click", () => {
  bannerDismissed = true; $("#abBanner").hidden = true;
  try { localStorage.setItem("abBanner", "off"); } catch {}
});

async function setAdminMode(on) {
  const msg = on
    ? "Para medir o FPS de todos os jogos (inclusive o CS2), o TURZX Studio precisa rodar como administrador, " +
      "como o app original da TURZX.\n\nO Windows vai pedir permissão UMA vez. Depois, o programa abre como " +
      "administrador ao ligar o PC (pelo Agendador de Tarefas), sem perguntar de novo, e reinicia agora.\n\nContinuar?"
    : "Desativar o modo administrador? O Windows vai pedir permissão para remover a tarefa agendada.";
  if (!confirm(msg)) return;
  const r = await fetch(`/api/admin_mode?on=${on ? 1 : 0}`, { method: "POST" }).then((x) => x.json()).catch(() => ({}));
  if (r.error) alert(r.error);
  pollStatus();
}

function renderSources(v, st = {}) {
  const ab = !!v.afterburner, rt = !!v.rtss, pm = v.presentmon === "PresentMon";
  $("#abBanner").hidden = ab || bannerDismissed;
  const line = (ok, name, okText, badText) =>
    el("p", {}, el("span", { class: ok ? "ok" : "bad" }, ok ? "✓ " : "✗ "), el("b", {}, name), " — ", ok ? okText : badText);
  const box = $("#sources"); box.innerHTML = "";
  let pmLine;
  if (pm) pmLine = line(true, "PresentMon", "ativo: FPS de todos os jogos, inclusive o CS2.", "");
  else if (st.admin_pending) pmLine = el("p", {}, "⏳ ", el("b", {}, "PresentMon"),
    " — aguardando a permissão do Windows. Se a janela não aparecer, procure o ícone piscando na barra de tarefas.");
  else pmLine = el("p", {}, el("span", { class: "bad" }, "✗ "), el("b", {}, "PresentMon"),
    st.admin_task ? " — modo administrador ativo; reinicie o TURZX Studio. " :
      " — inativo: precisa do modo administrador para medir jogos como o CS2. ",
    st.admin_task ? null : el("button", { onclick: () => setAdminMode(true) }, "Ativar FPS em todos os jogos"),
    st.admin_error ? el("span", { class: "bad" }, " " + st.admin_error) : null);
  box.append(
    pmLine,
    line(ab, "MSI Afterburner", "conectado: temperatura da CPU e dados completos da GPU.",
      "não encontrado. Sem ele não há temperatura da CPU (e GPUs AMD/Intel ficam sem dados)."),
    line(rt, "RivaTuner Statistics Server", "ativo: FPS de reserva (jogos que aceitam o RivaTuner).",
      "não encontrado (reserva do FPS)."),
    st.admin_task ? el("p", {}, "Modo administrador ativo. ",
      el("button", { onclick: () => setAdminMode(false) }, "Desativar")) : null,
    el("p", {}, `FPS agora: ${v.fps} ${v.fps_app ? "(" + v.fps_app + ")" : ""} ${v.fps_source ? "· via " + v.fps_source : ""}`),
    el("p", {}, "Dicas: deixe o Afterburner e o RivaTuner iniciando com o Windows; o RivaTuner precisa estar aberto ",
      "antes do jogo. No Afterburner, em Configurações → Monitoramento, deixe marcados \"CPU temperature\", ",
      "\"CPU power\" e \"Framerate\". Jogos como o CS2 bloqueiam o RivaTuner: neles o FPS vem do PresentMon."),
    el("p", {}, el("a", { href: "https://www.msi.com/Landing/afterburner/graphics-cards", target: "_blank" },
      "Baixar o MSI Afterburner (site oficial da MSI)")));
}

// ------------------------------------------------------------ status ao vivo

async function pollStatus() {
  try {
    const r = await api("/api/status");
    values = r.values;
    videoErrors = r.video_errors || {};
    const c = $("#conn");
    c.className = "pill " + (r.status.connected ? "ok" : "bad");
    c.textContent = r.status.connected ? `Conectada · ${r.status.fps} qps` : r.status.message;
    c.title = r.status.screen_id || "";
    if (liveIndex !== r.current) { liveIndex = r.current; renderScreens(); }
    const pinned = r.pinned != null;
    $("#pinScreen").dataset.pinned = pinned ? "1" : "0";
    renderSources(r.values, r);
    $("#pinScreen").textContent = pinned ? `Retomar carrossel (fixa: ${cfg.screens[r.pinned]?.name || r.pinned})` : "Mostrar agora";
  } catch {
    $("#conn").className = "pill bad"; $("#conn").textContent = "App fechado";
  }
}

function renderAll() {
  $("#screenTitle").textContent = screen() ? `${screen().name} · ${logicalSize().join("×")}` : "";
  fitStage(); renderOverlay(); renderLayers(); renderProps(); refreshPreview();
}

async function init() {
  const st = await api("/api/state");
  ({ config: cfg, catalog, fonts, media, values } = st);
  lastSaved = JSON.stringify(cfg);
  liveIndex = st.current;
  $("#ffmpegWarn").hidden = st.ffmpeg;
  Object.entries(TYPES).forEach(([k, t]) => $("#addWidget").append(el("button", { onclick: () => addWidget(k) }, t.label)));
  bindSettings(); renderSkins(); renderMedia(); renderScreens(); renderAll(); initLayouts();
  window.addEventListener("resize", fitStage);
  setInterval(refreshPreview, 1000);
  setInterval(pollStatus, 2000);
  pollStatus();
}
init();
