// The on-phone AI: turns words like "pink bunny with hearts" into a recipe.
//
// How it works: a small language model (all-MiniLM-L6-v2, about 23 MB)
// turns words into "meaning numbers" (embeddings). Words that mean similar
// things get similar numbers, so "kitty", "kitten" and "meow" all land near
// "cat". We compare what you typed against short descriptions of every
// character, effect, motion and color mood, and pick the closest ones.
// Everything runs on the phone. After the first download it works offline.

import { cleanRecipe, MAX_EXTRAS, MAX_TEXT } from "./looks.js";

const LIB = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.3.2/dist/transformers.min.js";
const MODEL = "Xenova/all-MiniLM-L6-v2";

// ---------- what the AI can choose from ----------

const CHARACTERS = {
  bunny: ["bunny", "rabbit", "hare"],
  cat: ["cat", "kitty", "kitten", "meow"],
  bear: ["teddy", "bear", "cub"],
  frog: ["frog", "toad"],
  ghost: ["ghost", "spooky", "halloween", "boo"],
  alien: ["alien", "ufo", "martian", "extraterrestrial"],
  heart: ["heart", "love", "valentine"],
  star: ["star", "celebrity", "superstar"],
  mushroom: ["mushroom", "shroom", "fungi", "toadstool"],
  cherry: ["cherry", "cherries", "fruit"],
  cloud: ["cloud", "fluffy", "sky", "weather"],
  moon: ["moon", "crescent", "night"],
  flower: ["flower", "blossom", "daisy", "petal"],
};

const EXTRAS = {
  hearts: ["hearts", "love"],
  sparkles: ["sparkles", "glitter", "sparkly", "shiny"],
  stars: ["stars", "twinkling", "starry"],
  bubbles: ["bubbles", "bubbly"],
  notes: ["music", "notes", "song", "singing"],
  rain: ["rain", "raindrops", "rainy", "crying"],
  confetti: ["confetti", "party", "celebration", "birthday"],
  zzz: ["sleepy", "sleeping", "tired", "zzz"],
};

const MOTIONS = {
  bounce: ["bouncing", "jumping", "hopping", "happy"],
  float: ["floating", "dreamy", "calm", "drifting", "sleepy", "flying"],
  sway: ["swaying", "swinging", "gentle"],
  shake: ["shaking", "angry", "scared", "nervous", "trembling"],
  pulse: ["pulsing", "beat", "bass", "drop"],
  dance: ["dancing", "rave", "party", "groove"],
};

// Color moods: used when you don't name a color yourself.
const MOODS = [
  { about: "cute sweet kawaii pastel soft",            main: "#ff9cc8", accent: "#ffffff", background: "#2a0f3d" },
  { about: "spooky halloween creepy dark gothic",      main: "#f2f2f2", accent: "#ff8a00", background: "#14002b" },
  { about: "ocean sea water beach wave",               main: "#6fd3ff", accent: "#ffffff", background: "#002a4d" },
  { about: "sunset summer warm tropical",              main: "#ff8a00", accent: "#ff2fa0", background: "#2b0a3d" },
  { about: "forest nature green garden plants",        main: "#8fe36b", accent: "#ff6ea8", background: "#0f2a14" },
  { about: "space galaxy cosmic night universe",       main: "#b9a2ff", accent: "#ffe600", background: "#0a0020" },
  { about: "rave neon techno edm festival",            main: "#39ff14", accent: "#ff2fa0", background: "#000000" },
  { about: "romantic love valentine date",             main: "#ff3b6b", accent: "#ffd1dc", background: "#2b0014" },
  { about: "angel heaven soft white pure",             main: "#ffffff", accent: "#ffb3d1", background: "#a9c8ff" },
  { about: "cozy autumn coffee fall warm",             main: "#c98a5a", accent: "#ffd29c", background: "#2a1810" },
  { about: "ice winter snow frozen cold",              main: "#dff6ff", accent: "#6fd3ff", background: "#0c2340" },
  { about: "cyber futuristic chrome robot y2k",        main: "#c0c8d8", accent: "#00e5ff", background: "#120024" },
];

// Color words (checked longest first, so "hot pink" wins over "pink").
const COLORS = {
  "hot pink": "#ff2fa0", "baby pink": "#ffc2dc", "light pink": "#ffc2dc", pink: "#ff9cc8",
  red: "#ff3b4a", orange: "#ff8a00", yellow: "#ffe600", gold: "#ffc83d",
  lime: "#b6ff3b", green: "#8fe36b", mint: "#7dffc8", teal: "#1ccfc0",
  "baby blue": "#a9d8ff", "light blue": "#a9d8ff", navy: "#1b2a6b", blue: "#3d9bff",
  purple: "#9b5cff", violet: "#9b5cff", lavender: "#c9b5ff", lilac: "#c9b5ff",
  white: "#ffffff", black: "#1a1a1a", brown: "#9c6c46", grey: "#a0a0a8", gray: "#a0a0a8",
  silver: "#c0c8d8", cream: "#fff4d6", peach: "#ffb38a", coral: "#ff7a6b",
};

// How sure the AI must be before adding an effect or a motion.
const CHARACTER_MIN = 0.5;
const MOOD_MIN = 0.6;
const EXTRA_MIN = 0.6;
const MOTION_MIN = 0.55;

const SKIP = new Set("a an the with and of in on at to for some lots lot many very really is are that this my me i it its make show please want like little tiny cute big".split(" "));

// ---------- loading the model ----------

let embedder = null;
const cache = new Map();   // text -> meaning numbers, so each label is only worked out once

// onProgress(fraction 0..1) is called while downloading the first time.
export async function loadAI(onProgress = () => {}) {
  if (embedder) return embedder;
  const { pipeline } = await import(LIB);
  const files = {};
  // "wasm" = the safe mode that worked on Alexia's iPhone without reloading.
  const pipe = await pipeline("feature-extraction", MODEL, {
    device: "wasm",
    dtype: "q8",
    progress_callback: (p) => {
      if (p.status === "progress" && p.total) {
        files[p.file] = [p.loaded, p.total];
        let got = 0, all = 0;
        for (const [a, b] of Object.values(files)) { got += a; all += b; }
        onProgress(got / all);
      }
    },
  });
  embedder = async (text) => Array.from((await pipe(text, { pooling: "mean", normalize: true })).data);
  return embedder;
}

// For testing on a laptop: hand in your own embed function.
export function useEmbedder(fn) { embedder = fn; cache.clear(); }

async function meaning(text) {
  if (!cache.has(text)) cache.set(text, await embedder(text));
  return cache.get(text);
}

const similar = (a, b) => a.reduce((s, x, i) => s + x * b[i], 0);

// Best match for each label: every word you typed is compared with every
// example word of the label, and the closest pair counts.
// Returns [{ name, score }] best first.
async function rank(labels, pieces) {
  const out = [];
  for (const [name, examples] of Object.entries(labels)) {
    let best = -1;
    for (const ex of examples) {
      const l = await meaning(ex);
      for (const p of pieces) best = Math.max(best, similar(l, p));
    }
    out.push({ name, score: best });
  }
  return out.sort((a, b) => b.score - a.score);
}

// ---------- the main thing ----------

// Returns { recipe, why } where why explains the choices (nice for a demo).
export async function design(prompt) {
  if (!embedder) throw new Error("Call loadAI() first");
  let text = "";
  let rest = prompt.trim();

  // Words in quotes, or after "saying"/"says"/"that says", become the text.
  const quoted = rest.match(/["“'‘]([^"”'’]+)["”'’]/);
  const saying = rest.match(/\b(?:that says|saying|says|with the words?|with text)\s+(.+)$/i);
  if (quoted) { text = quoted[1]; rest = rest.replace(quoted[0], " "); }
  else if (saying) { text = saying[1]; rest = rest.slice(0, saying.index); }
  text = text.trim().slice(0, MAX_TEXT);

  const lower = " " + rest.toLowerCase().replace(/[^a-z ]/g, " ").replace(/\s+/g, " ") + " ";
  const words = lower.trim().split(" ").filter((w) => w && !SKIP.has(w));

  // Colors you named, in the order you named them.
  const named = [];
  const bgMatch = lower.match(/ (?:on (?:a )?)?([a-z]+(?: [a-z]+)?) (?:background|bg) /);
  let bgColor = null;
  for (const c of Object.keys(COLORS).sort((a, b) => b.length - a.length)) {
    if (bgMatch && (bgMatch[1] === c || bgMatch[1].endsWith(" " + c))) { bgColor = COLORS[c]; continue; }
    const at = lower.indexOf(" " + c + " ");
    if (at >= 0 && !named.some((n) => n.at <= at && at < n.at + n.len)) named.push({ at, len: c.length + 1, hex: COLORS[c], word: c });
  }
  named.sort((a, b) => a.at - b.at);

  const colorWords = new Set(named.flatMap((n) => n.word.split(" ")));
  const meaningWords = words.filter((w) => !colorWords.has(w) && w !== "background" && w !== "bg");
  const whole = meaningWords.join(" ") || "cute";
  const pieces = [await meaning(whole)];
  for (const w of meaningWords) pieces.push(await meaning(w));

  // The words before "with" say WHO it is ("pink bunny"), the words after
  // say what's around it ("hearts"). So "bunny with hearts" stays a bunny.
  const head = lower.split(/ (?:with|and|plus|surrounded by|in|at|on) /)[0].trim().split(" ")
    .filter((w) => w && !SKIP.has(w) && !colorWords.has(w));
  const headPieces = [];
  for (const w of head) headPieces.push(await meaning(w));

  let chars = await rank(CHARACTERS, headPieces.length ? headPieces : pieces.slice(1));
  if (chars[0].score < CHARACTER_MIN) chars = await rank(CHARACTERS, pieces.slice(1).length ? pieces.slice(1) : pieces);
  const extras = await rank(EXTRAS, pieces.slice(1).length ? pieces.slice(1) : pieces);
  const motions = await rank(MOTIONS, pieces.slice(1).length ? pieces.slice(1) : pieces);
  // Mood: closest of all the mood words to any word you typed (or the whole sentence).
  const moodRank = [];
  for (const m of MOODS) {
    let best = -1;
    for (const w of m.about.split(" ")) {
      const l = await meaning(w);
      for (const p of pieces) best = Math.max(best, similar(l, p));
    }
    moodRank.push({ m, score: best });
  }
  moodRank.sort((a, b) => b.score - a.score);
  // A weak mood match means the words weren't about a mood: stay cute.
  const mood = moodRank[0].score >= MOOD_MIN ? moodRank[0].m : MOODS[0];

  // If nothing looks like a character ("just sparkles"), show no character.
  let character = chars[0].score >= CHARACTER_MIN ? chars[0].name : "none";
  const extraNames = extras.filter((e) => e.score >= EXTRA_MIN).slice(0, MAX_EXTRAS).map((e) => e.name);
  // Never send an empty screen: if nothing else matched, use the closest character anyway.
  if (character === "none" && !extraNames.length && !text) character = chars[0].name;

  const recipe = cleanRecipe({
    character,
    main: named[0]?.hex || mood.main,
    accent: named[1]?.hex || mood.accent,
    background: bgColor || named[2]?.hex || mood.background,
    extras: extraNames,
    motion: motions[0].score >= MOTION_MIN ? motions[0].name : "bounce",
    text,
  });
  if (!bgColor) fixContrast(recipe);

  const pct = (s) => Math.round(s * 100) + "%";
  const why = [
    character === "none" ? "No character matched, so just effects" : `Character: ${character} (${pct(chars[0].score)} match)`,
    named.length ? `Colors you named: ${named.map((n) => n.word).join(", ")}` : `Color mood: ${mood.about.split(" ")[0]}${mood === moodRank[0].m ? ` (${pct(moodRank[0].score)} match)` : " (default)"}`,
    recipe.extras.length ? `Effects: ${recipe.extras.join(", ")}` : "No effects matched",
    `Motion: ${recipe.motion}${motions[0].score >= MOTION_MIN ? ` (${pct(motions[0].score)} match)` : " (default)"}`,
  ];
  return { recipe, why };
}

// Make sure the character doesn't disappear into the background.
function fixContrast(r) {
  const lum = (h) => { const n = parseInt(h.slice(1), 16); return ((n >> 16) & 255) * 0.3 + ((n >> 8) & 255) * 0.59 + (n & 255) * 0.11; };
  if (Math.abs(lum(r.main) - lum(r.background)) < 60) {
    r.background = lum(r.main) > 128 ? "#1a0033" : "#fff4d6";
  }
}
