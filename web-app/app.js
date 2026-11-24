import { Clip } from "./clip-ble.js";
import { setupAI } from "./ai-ui.js";
import { setupDesigner } from "./scene-ui.js";
import { parseScheduleFile, setsAt, nowAndNext, testSchedule, fmtTime, nearestStage } from "./schedule.js";

const clip = new Clip();
const $ = (id) => document.getElementById(id);

// ---------- Saved on this phone ----------
function load(key, fallback) {
  try { const v = JSON.parse(localStorage.getItem("raveclip." + key)); return v ?? fallback; }
  catch (e) { return fallback; }
}
function save(key, value) {
  try { localStorage.setItem("raveclip." + key, JSON.stringify(value)); } catch (e) {}
}

let artists = load("artists", ["ROZ"]);
let schedule = load("schedule", null);
let stage = load("stage", null);
let autoOn = load("auto", false);
let locOn = load("loc", false);
let current = "";   // what's on the clip ("" = bunny face)
let aiLine = null;  // the AI look on the clip right now, if any
let sceneLine = null;  // the designed scene on the clip right now, if any

// ---------- Manual buttons ----------
function renderArtists() {
  const box = $("artists");
  box.innerHTML = "";
  box.appendChild(makeButton("", "🐰 Bunny face (no artist)", "bunny"));
  artists.forEach((name) => box.appendChild(makeButton(name, name)));
  $("nowShowing").textContent = current || "bunny face";
}

function makeButton(value, label, extraClass) {
  const b = document.createElement("button");
  b.textContent = label;
  if (extraClass) b.classList.add(extraClass);
  if (!autoOn && value === current) b.classList.add("active");
  b.addEventListener("click", () => showByHand(value));
  if (value) {
    let timer;
    const start = () => { timer = setTimeout(() => removeArtist(value), 700); };
    const cancel = () => clearTimeout(timer);
    b.addEventListener("touchstart", start, { passive: true });
    b.addEventListener("touchend", cancel);
    b.addEventListener("touchmove", cancel);
    b.addEventListener("contextmenu", (e) => { e.preventDefault(); removeArtist(value); });
  }
  return b;
}

function removeArtist(name) {
  if (!confirm(`Remove ${name}?`)) return;
  artists = artists.filter((a) => a !== name);
  save("artists", artists);
  renderArtists();
}

async function showByHand(name) {
  if (autoOn) setAuto(false, { silent: true });
  current = name;
  aiLine = null;
  sceneLine = null;
  renderAll();
  try {
    const sent = await clip.send(name);
    if (!sent) setStatus("disconnected", null, "Not connected. It'll send when you connect.");
  } catch (e) {
    setStatus("disconnected", null, "Couldn't send. Try again.");
  }
}

$("addForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const name = $("addInput").value.trim();
  if (!name) return;
  if (!artists.includes(name)) artists.push(name);
  save("artists", artists);
  $("addInput").value = "";
  showByHand(name);
});

// ---------- Festival schedule ----------
function useSchedule(s) {
  schedule = s;
  save("schedule", s);
  if (!stage || !s.stages.some((x) => x.name === stage)) {
    stage = s.stages[0].name;
    save("stage", stage);
  }
  $("pickList").hidden = true;
  renderAll();
  if (autoOn) sendAuto();
}

$("fileInput").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    useSchedule(parseScheduleFile(await file.text(), file.name));
  } catch (err) {
    alert("Couldn't read that file. " + err.message);
  }
  e.target.value = "";
});

$("pickBtn").addEventListener("click", async () => {
  const box = $("pickList");
  if (!box.hidden) { box.hidden = true; return; }
  box.innerHTML = "";
  const add = (label, getter) => {
    const b = document.createElement("button");
    b.textContent = label;
    b.addEventListener("click", async () => {
      try { useSchedule(await getter()); }
      catch (err) { alert("Couldn't load that festival. " + err.message); }
    });
    box.appendChild(b);
  };
  add("🧪 Test run (starts now, 7 minutes)", async () => testSchedule());
  try {
    const list = await (await fetch("schedules/index.json", { cache: "no-store" })).json();
    for (const f of list) {
      add(f.name, async () => {
        const r = await fetch("schedules/" + f.file, { cache: "no-store" });
        return parseScheduleFile(await r.text(), f.file);
      });
    }
  } catch (e) { /* offline: only the test run is offered */ }
  box.hidden = false;
});

function renderFestival() {
  $("festName").textContent = schedule ? schedule.festival : "No schedule yet";
  $("festBody").hidden = !schedule;
  if (!schedule) return;

  const chips = $("stages");
  chips.innerHTML = "";
  for (const st of schedule.stages) {
    const b = document.createElement("button");
    b.textContent = (st.lat != null ? "📍 " : "") + st.name;
    if (st.name === stage) b.classList.add("active");
    b.addEventListener("click", () => {
      if (locOn) setLoc(false);   // picking by hand turns location off
      changeStage(st.name);
    });
    chips.appendChild(b);
  }

  $("autoToggle").checked = autoOn;
  $("locToggle").checked = locOn;
  $("saveSpotName").textContent = stage;
  renderLocInfo();
  const sets = setsAt(schedule, stage);
  const now = new Date();
  const { current: on, next } = nowAndNext(sets, now);
  let line = on ? `Playing now: <b>${esc(on.artist)}</b> until ${fmtTime(on.end)}` : "Nobody on right now (bunny face)";
  if (next) line += `<br>Next: <b>${esc(next.artist)}</b> at ${fmtTime(next.start)}`;
  $("nowNext").innerHTML = line;

  const list = $("lineup");
  list.innerHTML = "";
  let lastDay = "";
  for (const s of sets) {
    const day = s.start.toLocaleDateString([], { weekday: "long", month: "short", day: "numeric" });
    if (day !== lastDay) {
      const d = document.createElement("li");
      d.className = "day";
      d.textContent = day;
      list.appendChild(d);
      lastDay = day;
    }
    const li = document.createElement("li");
    if (s === on) li.className = "on";
    else if (s.end <= now) li.className = "done";
    li.innerHTML = `<span>${esc(s.artist)}</span><span class="t">${fmtTime(s.start)} – ${fmtTime(s.end)}</span>`;
    list.appendChild(li);
  }
}

function esc(t) {
  return String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function changeStage(name) {
  if (name === stage) return;
  stage = name;
  save("stage", stage);
  renderAll();
  if (autoOn) sendAuto();
}

// ---------- Location: which stage am I at? ----------
// While the app is open, the phone checks where you are. When you've been
// close to a different stage for 20 seconds, it switches to that stage's
// lineup and sends it to the clip. (While the phone is locked, the clip
// keeps playing the last stage's lineup.)
let watchId = null;
let lastFix = null;        // { lat, lon, accuracy }
let locMessage = "";
let candidate = null, candidateSince = 0;
let savingSpot = false;
const SWITCH_AFTER_MS = 20000;
const WORST_ACCURACY_M = 150;

function hasSpots() {
  return !!schedule && schedule.stages.some((st) => st.lat != null);
}

function startWatching() {
  if (watchId !== null || !navigator.geolocation) return;
  watchId = navigator.geolocation.watchPosition(onPosition, onLocError, {
    enableHighAccuracy: true, maximumAge: 5000, timeout: 30000,
  });
}
function stopWatching() {
  if (watchId !== null) navigator.geolocation.clearWatch(watchId);
  watchId = null;
}

function onPosition(pos) {
  const { latitude: lat, longitude: lon, accuracy } = pos.coords;
  lastFix = { lat, lon, accuracy };
  if (!savingSpot) locMessage = "";
  if (locOn && schedule) {
    const near = nearestStage(schedule.stages, lat, lon);
    if (near && near.inside && accuracy <= WORST_ACCURACY_M && near.stage.name !== stage) {
      if (candidate !== near.stage.name) {
        candidate = near.stage.name;
        candidateSince = Date.now();
      } else if (Date.now() - candidateSince >= SWITCH_AFTER_MS) {
        candidate = null;
        changeStage(near.stage.name);
      }
    } else {
      candidate = null;
    }
  }
  renderLocInfo();
}

function onLocError(err) {
  if (err.code === 1) {
    locMessage = "Location is blocked. Allow it for Bluefy in iPhone Settings → Privacy & Security → Location Services → Bluefy → While Using the App.";
    if (locOn) setLoc(false, { keepMessage: true });
  } else {
    locMessage = "Can't find your location right now. Still trying…";
  }
  renderLocInfo();
}

function renderLocInfo() {
  const box = $("locInfo");
  if (locMessage) { box.textContent = locMessage; return; }
  if (!locOn) { box.textContent = ""; return; }
  if (!hasSpots()) {
    box.textContent = "No stage spots saved yet. Stand at a stage, tap it above, then tap the save button below.";
    return;
  }
  if (!lastFix) { box.textContent = "Finding you…"; return; }
  const near = nearestStage(schedule.stages, lastFix.lat, lastFix.lon);
  let t = `Closest: ${near.stage.name}, about ${Math.round(near.distance)} m away`;
  if (!near.inside) t += `. Too far to count, staying on ${stage}`;
  else if (candidate) {
    const left = Math.max(0, Math.ceil((SWITCH_AFTER_MS - (Date.now() - candidateSince)) / 1000));
    t += `. Switching in ${left} s…`;
  }
  if (lastFix.accuracy > WORST_ACCURACY_M) t += ". GPS is fuzzy right now, waiting for a better signal.";
  box.textContent = t;
}

function setLoc(on, { keepMessage } = {}) {
  locOn = on;
  save("loc", on);
  if (!keepMessage) locMessage = "";
  candidate = null;
  if (on) {
    if (!navigator.geolocation) locMessage = "This browser can't use your location.";
    else startWatching();
  } else {
    stopWatching();
  }
  renderAll();
}

$("locToggle").addEventListener("change", (e) => setLoc(e.target.checked));

// Save where you're standing as the chosen stage's spot.
$("saveSpotBtn").addEventListener("click", () => {
  if (!schedule || !navigator.geolocation) return;
  const btn = $("saveSpotBtn");
  savingSpot = true;
  btn.disabled = true;
  locMessage = "Getting a good GPS fix…";
  renderLocInfo();
  const done = () => { savingSpot = false; btn.disabled = false; };
  navigator.geolocation.getCurrentPosition((pos) => {
    done();
    const st = schedule.stages.find((x) => x.name === stage);
    st.lat = pos.coords.latitude;
    st.lon = pos.coords.longitude;
    save("schedule", schedule);
    lastFix = { lat: st.lat, lon: st.lon, accuracy: pos.coords.accuracy };
    locMessage = `Saved! This spot is now ${stage}` +
      (pos.coords.accuracy > 50 ? ` (GPS was fuzzy, ±${Math.round(pos.coords.accuracy)} m. Try again in the open if it acts weird).` : ".");
    renderAll();
  }, (err) => { done(); onLocError(err); },
  { enableHighAccuracy: true, maximumAge: 0, timeout: 30000 });
});

// ---------- Auto mode ----------
// The clip gets the whole lineup for your stage and switches by itself,
// so it keeps going even when your phone is locked.
async function sendAuto() {
  if (!schedule || !clip.connected) return;
  if (!clip.canAuto) {
    setStatus("connected", null, "Your clip needs the new code for auto-switch (see the guide).");
    return;
  }
  try {
    await clip.sendSchedule(setsAt(schedule, stage));
  } catch (e) {
    setStatus("disconnected", null, "Couldn't send the lineup. Try again.");
  }
}

function setAuto(on, { silent } = {}) {
  autoOn = on;
  save("auto", on);
  renderAll();
  if (on) sendAuto();
  else if (!silent) clip.send(current).catch(() => {});
}

$("autoToggle").addEventListener("change", (e) => setAuto(e.target.checked));

// Keep the screen's "now playing" up to date.
setInterval(() => {
  if (autoOn && schedule) {
    const { current: on } = nowAndNext(setsAt(schedule, stage));
    current = on ? on.artist : "";
  }
  renderAll();
}, 5000);

function renderAll() {
  if (autoOn && schedule) {
    const { current: on } = nowAndNext(setsAt(schedule, stage));
    current = on ? on.artist : "";
  }
  renderFestival();
  renderArtists();
}

// ---------- Connecting ----------
function setStatus(state, name, text) {
  $("dot").className = "dot " + state;
  const words = {
    connected: `Connected to ${name || "your clip"} ♡`,
    connecting: "Connecting…",
    disconnected: "Not connected",
  };
  $("statusText").textContent = text || words[state];
  $("connectBtn").textContent = state === "connected" ? "Disconnect" : "Connect to my clip";
  // the little pill in the top corner
  $("pill").className = "pill " + state;
  $("pillDot").className = "dot " + state;
  $("pillText").textContent = { connected: "Connected", connecting: "Connecting…", disconnected: "Connect" }[state];
}
clip.onStatus = (state, name) => setStatus(state, name);

// After every (re)connect, put the clip back in the right state.
clip.onReady = async () => {
  if (sceneLine && clip.canScene) await clip.sendScene(sceneLine);
  else if (aiLine && clip.canAI) await clip.sendLook(aiLine);
  else if (autoOn && schedule) await sendAuto();
  else await clip.send(current);
};

async function toggleConnection() {
  if (clip.connected) { clip.disconnect(); return; }
  try {
    await clip.connect();
  } catch (e) {
    if (e && e.name === "NotFoundError") setStatus("disconnected");
    else setStatus("disconnected", null, "Couldn't connect. Is the clip on and close by?");
  }
}
$("connectBtn").addEventListener("click", toggleConnection);
$("pill").addEventListener("click", toggleConnection);

if (!Clip.supported()) {
  $("unsupported").hidden = false;
  $("connectBtn").disabled = true;
  $("pill").disabled = true;
}

// Sends a scene line (from Design mode or from her trained AI).
async function sendSceneLine(line, label, status) {
  if (autoOn) setAuto(false, { silent: true });
  sceneLine = line;
  aiLine = null;
  current = label;
  renderAll();
  if (!clip.connected) {
    try {
      await clip.connect();
      status(clip.canScene ? "Sent to your clip ✨" : "Your clip needs the new code for scenes (see the guide).");
    } catch (e) { status("Not connected. Is the clip on and close by?"); }
    return;
  }
  if (!clip.canScene) { status("Your clip needs the new code for scenes (see the guide)."); return; }
  try { await clip.sendScene(line); status("Sent to your clip ✨"); }
  catch (e) { status("Couldn't send. Try again."); }
}

// ---------- AI looks ----------
const ai = setupAI({
  onSend: async (line, label) => {
    if (autoOn) setAuto(false, { silent: true });
    aiLine = line;
    sceneLine = null;
    current = "✨ " + label;
    renderAll();
    if (!clip.connected) {
      // Connecting sends the look by itself once it's done (see onReady).
      try {
        await clip.connect();
        ai.status(clip.canAI ? "Sent to your clip ✨" : "Your clip needs the new code for AI looks (see the guide).");
      }
      catch (e) { ai.status("Not connected. Is the clip on and close by?"); }
      return;
    }
    if (!clip.canAI) { ai.status("Your clip needs the new code for AI looks (see the guide)."); return; }
    try {
      await clip.sendLook(line);
      ai.status("Sent to your clip ✨");
    } catch (e) {
      ai.status("Couldn't send. Try again.");
    }
  },
  onSendScene: (line, label) => sendSceneLine(line, "✨ " + label, (t) => ai.status(t)),
  onEdit: (scene) => { designer.set(scene); showMode("design"); designer.status("From your AI ✨ Change anything you like."); },
});

// ---------- Design it yourself (scenes) ----------
const designer = setupDesigner({
  onSend: (line, label) => sendSceneLine(line, "🎛 " + label, (t) => designer.status(t)),
});

// AI / Design switch at the top of the Create tab
function showMode(m) {
  $("modeAI").hidden = m !== "ai";
  $("modeDesign").hidden = m !== "design";
  document.querySelectorAll(".seg button").forEach((b) => b.classList.toggle("active", b.dataset.mode === m));
  save("createMode", m);
}
document.querySelectorAll(".seg button").forEach((b) => b.addEventListener("click", () => showMode(b.dataset.mode)));
showMode(load("createMode", "design"));

if ("serviceWorker" in navigator) {
  // Keeps the app and the AI library on the phone for no-signal use.
  // (Some browsers like Bluefy may not allow this. The app works anyway.)
  navigator.serviceWorker.register("sw.js").catch(() => {});
}

// ---------- Tabs ----------
function showTab(name) {
  document.querySelectorAll(".view").forEach((v) => {
    const on = v.dataset.view === name;
    v.hidden = !on;
    if (on) $("viewTitle").textContent = v.dataset.title;
  });
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  save("tab", name);
  window.scrollTo(0, 0);
}
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => showTab(t.dataset.tab)));
showTab(load("tab", "create"));
addEventListener("scroll", () => {
  document.querySelector(".topbar").classList.toggle("scrolled", scrollY > 4);
}, { passive: true });

if (locOn) startWatching();
renderAll();
