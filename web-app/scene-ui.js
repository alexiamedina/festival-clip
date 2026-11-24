// "Design" mode of the Create tab: build a scene by hand with a live preview.
// The trained AI will later fill in these same choices from a sentence.

import { drawScene, sceneToLine, lineToScene, cleanScene, DEFAULT_SCENE,
  EFFECTS, STYLES, BACKGROUNDS, MOVES, HAIRS } from "./scene.js";

const $ = (id) => document.getElementById(id);
function load(key, fallback) {
  try { const v = JSON.parse(localStorage.getItem("raveclip." + key)); return v ?? fallback; }
  catch (e) { return fallback; }
}
function save(key, value) {
  try { localStorage.setItem("raveclip." + key, JSON.stringify(value)); } catch (e) {}
}

const SWATCHES = ["FFFFFF", "000000", "1A0033", "3B2B2E", "F7EEDD", "FF9CC8", "FF2FA0", "FF4A55", "FF9A3C",
  "FFE14D", "8FE36B", "7DFFC8", "5AA8FF", "2F3A9E", "A06BFF", "C9B5FF"];

const LABELS = {
  fx: { still: "Still", scroll: "Scroll", wave: "Wave", bounce: "Bounce", invert: "Invert flash", rainbow: "Rainbow",
        glitch: "Glitch", type: "Typewriter", pulse: "Pulse" },
  st: { plain: "Plain", shadow: "Shadow", outline: "Bubble" },
  bp: { solid: "Solid", gradient: "Gradient", checker: "Checker", stripes: "Stripes", dots: "Dots", stars: "Stars",
        hearts: "Hearts", sparkles: "Sparkles", rainbow: "Rainbow" },
  av: { none: "Off", smile: "Smile", teeth: "Bunny teeth", ooh: "Ooh", grin: "Big smile", chill: "Chill",
        dance1: "Dance 1", dance2: "Dance 2", dance3: "Dance 3" },
  hr: { straight: "Straight", curly: "Curly" },
  sp: { 1: "Slow", 2: "Medium", 3: "Fast" },
};

const PRESETS = [
  { name: "ROZ flash", fx: "invert", sp: 3, st: "plain", fg: "FFE14D", ac: "FF2FA0", bg: "000000", b2: "FF2FA0", bp: "solid", av: "none", t: "ROZ" },
  { name: "PLUR bubble", fx: "wave", sp: 2, st: "outline", fg: "FFFFFF", ac: "FF2FA0", bg: "FF9CC8", b2: "FFFFFF", bp: "stars", av: "none", t: "PLUR" },
  { name: "Dancing me", fx: "bounce", sp: 2, st: "shadow", fg: "FFFFFF", ac: "A06BFF", bg: "1A0033", b2: "FF9CC8", bp: "sparkles", av: "dance1", t: "HI!" },
  { name: "Rainbow rave", fx: "rainbow", sp: 2, st: "shadow", fg: "FFFFFF", ac: "000000", bg: "000000", b2: "FFFFFF", bp: "checker", av: "none", t: "RAVE" },
  { name: "Glitch techno", fx: "glitch", sp: 3, st: "plain", fg: "7DFFC8", ac: "FF2FA0", bg: "000000", b2: "2F3A9E", bp: "stripes", av: "none", t: "TECHNO" },
  { name: "Kiss me", fx: "pulse", sp: 2, st: "outline", fg: "FFFFFF", ac: "FF2FA0", bg: "FF9CC8", b2: "FFFFFF", bp: "hearts", av: "ooh", t: "XOXO" },
];

export function setupDesigner({ onSend }) {
  let scene = cleanScene(load("scene", DEFAULT_SCENE));
  let saved = load("scenes", []);       // [{ line, label }]
  const canvas = $("sceneCanvas");
  const ctx = canvas.getContext("2d");
  const t0 = performance.now();

  function status(text) { $("scStatus").textContent = text; }

  function chips(boxId, key, values) {
    const box = $(boxId);
    box.innerHTML = "";
    values.forEach((v) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = LABELS[key][v] ?? v;
      if (String(scene[key]) === String(v)) b.classList.add("active");
      b.addEventListener("click", () => set({ [key]: v }));
      box.appendChild(b);
    });
  }

  function swatches(boxId, key) {
    const box = $(boxId);
    box.innerHTML = "";
    SWATCHES.forEach((c) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "swatch" + (scene[key] === c ? " active" : "");
      b.style.background = "#" + c;
      b.setAttribute("aria-label", "#" + c);
      b.addEventListener("click", () => set({ [key]: c }));
      box.appendChild(b);
    });
  }

  function render() {
    chips("scFx", "fx", EFFECTS);
    chips("scSp", "sp", [1, 2, 3]);
    chips("scSt", "st", STYLES);
    chips("scBp", "bp", BACKGROUNDS);
    chips("scAv", "av", MOVES);
    chips("scHr", "hr", HAIRS);
    swatches("scFg", "fg");
    swatches("scAc", "ac");
    swatches("scBg", "bg");
    swatches("scB2", "b2");
    if (document.activeElement !== $("scText")) $("scText").value = scene.t;
    renderSaved();
  }

  function set(change) {
    scene = cleanScene({ ...scene, ...change });
    save("scene", scene);
    render();
  }

  function renderSaved() {
    const box = $("scSaved");
    box.innerHTML = "";
    $("scSavedTitle").hidden = !saved.length;
    saved.forEach((s, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = s.label;
      b.addEventListener("click", () => set(lineToScene(s.line)));
      b.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        if (confirm(`Remove "${s.label}"?`)) { saved.splice(i, 1); save("scenes", saved); renderSaved(); }
      });
      let timer;
      b.addEventListener("touchstart", () => { timer = setTimeout(() => b.dispatchEvent(new Event("contextmenu")), 700); }, { passive: true });
      b.addEventListener("touchend", () => clearTimeout(timer));
      b.addEventListener("touchmove", () => clearTimeout(timer));
      box.appendChild(b);
    });
  }

  PRESETS.forEach((p) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = p.name;
    b.addEventListener("click", () => set(p));
    $("scPresets").appendChild(b);
  });

  $("scText").addEventListener("input", (e) => set({ t: e.target.value }));
  $("scSend").addEventListener("click", () => onSend(sceneToLine(scene), scene.t || LABELS.bp[scene.bp]));
  $("scSave").addEventListener("click", () => {
    const line = sceneToLine(scene);
    if (saved.some((s) => s.line === line)) return;
    saved.unshift({ line, label: (scene.t || "scene") + " · " + LABELS.fx[scene.fx].toLowerCase() });
    saved = saved.slice(0, 16);
    save("scenes", saved);
    renderSaved();
    status("Saved ♡");
  });

  function frame() {
    if (canvas.offsetParent !== null) drawScene(ctx, scene, (performance.now() - t0) / 1000);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  render();

  return { status, set, get scene() { return scene; } };
}
