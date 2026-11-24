// The "Design with AI" card: type words, the on-phone AI makes a look,
// you see a live preview, then send it to the clip.

import { loadAI, design } from "./ai-designer.js";
import { drawLook, toLine, fromLine } from "./looks.js";
import { hasSceneAI, loadSceneAI, makeScene } from "./scene-ai.js";
import { drawScene, sceneToLine, lineToScene } from "./scene.js";

const $ = (id) => document.getElementById(id);

function load(key, fallback) {
  try { const v = JSON.parse(localStorage.getItem("raveclip." + key)); return v ?? fallback; }
  catch (e) { return fallback; }
}
function save(key, value) {
  try { localStorage.setItem("raveclip." + key, JSON.stringify(value)); } catch (e) {}
}

// Ideas for Alexia's own trained AI (scenes: words, effects, backgrounds, mini-me)
const SCENE_IDEAS = ["ROZ invert colors fast", "PLUR in pink bubble letters with hearts", 'me dancing and "HI!"',
  "TECHNO glitchy on black", "slow wavy FISHER on a starry sky", "I LOVE ROZ rainbow text with me blowing a kiss",
  "sparkly purple background with XOXO", "write BASS in yellow, pulsing"];
const IDEAS = ["pink bunny with hearts", "sleepy kitty", "frog dancing at a rave", "spooky ghost",
  "galaxy star", "crying cloud", "mint frog with bubbles", 'cherry saying "PLUR"'];

// onSend(line, label) sends an old-style look, onSendScene(line, label) a scene,
// onEdit(scene) opens a scene in Design mode.
export function setupAI({ onSend, onSendScene, onEdit }) {
  let ready = null;           // the model loading promise
  let current = null;         // { kind: "scene" | "look", line, label }
  let trained = false;        // true once her trained model (scene-ai.bin) is in the app
  let saved = load("looks", []);   // [{ line, label }]
  const canvas = $("aiCanvas");
  const ctx = canvas.getContext("2d");
  const t0 = performance.now();

  function status(text) { $("aiStatus").textContent = text; }

  function startLoading() {
    if (ready) return ready;
    status("Waking up the AI… (the first time it downloads about 23 MB)");
    const loader = trained ? loadSceneAI : loadAI;
    ready = loader((f) => status(`Downloading the AI: ${Math.round(f * 100)}%`))
      .then(() => status(trained ? "Your trained AI is ready ✨ Runs on your phone, no signal needed."
                                 : "AI ready ✨ Runs on your phone, no signal needed."))
      .catch((e) => {
        ready = null;
        status("Couldn't load the AI. Check your internet the first time, then try again.");
        throw e;
      });
    return ready;
  }

  function show(line, label, why, kind = "look") {
    current = { kind, line, label };
    $("aiEmpty").hidden = true;
    $("aiSend").hidden = false;
    $("aiSave").hidden = false;
    $("aiEdit").hidden = kind !== "scene";
    $("aiWhy").innerHTML = "";
    (why || []).forEach((w) => {
      const li = document.createElement("li");
      li.textContent = w;
      $("aiWhy").appendChild(li);
    });
  }

  async function make(prompt) {
    prompt = prompt.trim();
    if (!prompt) return;
    $("aiInput").value = prompt;
    try { await startLoading(); } catch (e) { return; }
    status("Thinking…");
    const started = performance.now();
    try {
      if (trained) {
        const r = await makeScene(prompt);
        if (!r) return;
        const ms = Math.round(performance.now() - started);
        show(sceneToLine(r.scene), prompt, explain(r), "scene");
        status(`Made by your AI in ${ms < 1000 ? ms + " ms" : (ms / 1000).toFixed(1) + " s"} ✨`);
        return;
      }
      const { recipe, why } = await design(prompt);
      const ms = Math.round(performance.now() - started);
      show(toLine(recipe), prompt, why);
      status(`Made on your phone in ${ms < 1000 ? ms + " ms" : (ms / 1000).toFixed(1) + " s"} ✨`);
    } catch (e) {
      status("The AI got confused. Try different words.");
    }
  }

  // What the trained AI decided, and how sure it was.
  function explain(r) {
    const f = r.fields, pct = (k) => Math.round(f[k].sure * 100) + "%";
    const s = r.scene;
    return [
      s.t ? `Words on your clip: "${s.t}"` : "No words picked out, so just the look",
      `Effect: ${s.fx}, ${["slow", "medium", "fast"][s.sp - 1]} (${pct("fx")} sure)`,
      `Letters: ${s.st}, #${s.fg} (${pct("fg")} sure)`,
      `Background: ${s.bp}, #${s.bg} (${pct("bp")} sure)`,
      s.av === "none" ? `Mini me: off (${pct("av")} sure)` : `Mini me: ${s.av}, ${s.hr} hair (${pct("av")} sure)`,
    ];
  }

  // Animate the preview.
  function frame() {
    const t = (performance.now() - t0) / 1000;
    if (current?.kind === "scene") drawScene(ctx, lineToScene(current.line), t);
    else if (current) drawLook(ctx, fromLine(current.line), t);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  function renderSaved() {
    const box = $("aiSaved");
    box.innerHTML = "";
    $("aiSavedTitle").hidden = !saved.length;
    saved.forEach((s, i) => {
      const b = document.createElement("button");
      b.textContent = s.label;
      b.addEventListener("click", () => { show(s.line, s.label, null, s.kind || "look"); status("One of your saved looks."); });
      b.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        if (confirm(`Remove "${s.label}"?`)) { saved.splice(i, 1); save("looks", saved); renderSaved(); }
      });
      let timer;
      b.addEventListener("touchstart", () => { timer = setTimeout(() => b.dispatchEvent(new Event("contextmenu")), 700); }, { passive: true });
      b.addEventListener("touchend", () => clearTimeout(timer));
      b.addEventListener("touchmove", () => clearTimeout(timer));
      box.appendChild(b);
    });
  }

  function renderIdeas() {
    $("aiIdeas").innerHTML = "";
    (trained ? SCENE_IDEAS : IDEAS).forEach((idea) => {
      const b = document.createElement("button");
      b.textContent = idea;
      b.addEventListener("click", () => make(idea));
      $("aiIdeas").appendChild(b);
    });
  }
  renderIdeas();
  // Use her trained model if scene-ai.bin is in the app folder.
  hasSceneAI().then((yes) => {
    if (!yes || ready) return;
    trained = true;
    renderIdeas();
    $("aiInput").placeholder = "ROZ invert colors fast…";
    $("aiHint").textContent = "Your own trained AI: it picks the words, effect, colors, background and mini me.";
    status("Your own trained AI runs right on your phone. No signal needed once it's loaded.");
  });

  $("aiForm").addEventListener("submit", (e) => { e.preventDefault(); make($("aiInput").value); });
  $("aiInput").addEventListener("focus", () => { startLoading().catch(() => {}); });
  $("aiSend").addEventListener("click", () => {
    if (!current) return;
    if (current.kind === "scene") onSendScene(current.line, current.label);
    else onSend(current.line, current.label);
  });
  $("aiEdit").addEventListener("click", () => { if (current?.kind === "scene") onEdit(lineToScene(current.line)); });
  $("aiSave").addEventListener("click", () => {
    if (!current || saved.some((s) => s.line === current.line)) return;
    saved.unshift(current);
    saved = saved.slice(0, 12);
    save("looks", saved);
    renderSaved();
  });
  renderSaved();

  return { status };
}
