// Draws an AI "look" (a recipe) exactly the way the clip does, so the
// phone can show a preview before sending. The clip's copy of this is
// festival_clip/ai_look.h. If you change one, change the other.
//
// A recipe:
//   { character: "bunny", main: "#ff9cc8", accent: "#ffffff", background: "#1a0033",
//     extras: ["hearts", "sparkles"], motion: "bounce", text: "" }
//
// Over Bluetooth it travels as one short line (see PROTOCOL.md):
//   bunny|FF9CC8|FFFFFF|1A0033|hearts,sparkles|bounce|

import { SPRITES } from "./sprites.js";

export const CHARACTERS = [...Object.keys(SPRITES), "none"];
export const EXTRAS = ["hearts", "sparkles", "stars", "bubbles", "notes", "rain", "confetti", "zzz"];
export const MOTIONS = ["bounce", "float", "sway", "shake", "pulse", "dance"];
export const MAX_EXTRAS = 3;
export const MAX_TEXT = 16;

export const SCREEN_W = 320, SCREEN_H = 170;
const N = 24;          // sprites are 24 x 24
const SCALE = 5;       // each sprite pixel = 5 x 5 screen pixels
const U = 4;           // effect pixel size
const OUTLINE = 0x2B1B2E;

// ---------- recipe <-> Bluetooth line ----------

const hex6 = (c) => {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(c || "").trim());
  return m ? m[1].toUpperCase() : null;
};

// Makes any recipe safe: unknown values become defaults, text gets trimmed.
export function cleanRecipe(r = {}) {
  const extras = (Array.isArray(r.extras) ? r.extras : [])
    .map((e) => String(e).toLowerCase())
    .filter((e, i, a) => EXTRAS.includes(e) && a.indexOf(e) === i)
    .slice(0, MAX_EXTRAS);
  const text = String(r.text || "")
    .toUpperCase()
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/Ø/g, "O")
    .replace(/[^ -~]/g, "")
    .replace(/\|/g, "")
    .trim()
    .slice(0, MAX_TEXT);
  return {
    character: CHARACTERS.includes(r.character) ? r.character : "bunny",
    main: "#" + (hex6(r.main) || "FF9CC8"),
    accent: "#" + (hex6(r.accent) || "FFFFFF"),
    background: "#" + (hex6(r.background) || "1A0033"),
    extras,
    motion: MOTIONS.includes(r.motion) ? r.motion : "bounce",
    text,
  };
}

export function toLine(recipe) {
  const r = cleanRecipe(recipe);
  return [r.character, hex6(r.main), hex6(r.accent), hex6(r.background),
    r.extras.join(","), r.motion, r.text].join("|");
}

export function fromLine(line) {
  const [character, main, accent, background, extras, motion, text] = String(line).split("|");
  return cleanRecipe({ character, main, accent, background,
    extras: extras ? extras.split(",") : [], motion, text });
}

// ---------- drawing (same math as the clip) ----------

const toInt = (c) => parseInt(hex6(c) || "000000", 16);
const css = (n) => "#" + (n >>> 0).toString(16).padStart(6, "0").slice(-6);
function shade(c, f) {
  const r = Math.floor(((c >> 16) & 255) * f), g = Math.floor(((c >> 8) & 255) * f), b = Math.floor((c & 255) * f);
  return (r << 16) | (g << 8) | b;
}
function light(c) {   // is this a light color?
  return ((c >> 16) & 255) * 3 + ((c >> 8) & 255) * 6 + (c & 255) > 1400;
}
function mix(a, b) {
  let h = (Math.imul(a, 2654435761) ^ Math.imul(b, 40503)) >>> 0;
  h = (h ^ (h >>> 15)) >>> 0;
  h = Math.imul(h, 2246822519) >>> 0;
  h = (h ^ (h >>> 13)) >>> 0;
  return h;
}
const fmod = (a, b) => a - b * Math.floor(a / b);

const ICONS = {
  hearts:  ["XX.XX", "XXXXX", "XXXXX", ".XXX.", "..X.."],
  stars:   ["..X..", ".XXX.", "XXXXX", ".XXX.", ".X.X."],
  notes:   ["..XX", "..XX", "..X.", "..X.", "XXX.", "XXX."],
  bubbles: [".XX.", "X..X", "X..X", ".XX."],
  zzz:     ["XXXX", "..X.", ".X..", "XXXX"],
  rain:    ["X", "X", "X"],
  confetti:["XX", "XX"],
};

// How each effect moves: rise up, fall down, or twinkle in place.
const EFFECT = {
  hearts:   { how: "rise", count: 6, speed: 0.25 },
  bubbles:  { how: "rise", count: 6, speed: 0.3 },
  notes:    { how: "rise", count: 5, speed: 0.3 },
  zzz:      { how: "rise", count: 3, speed: 0.2 },
  rain:     { how: "fall", count: 10, speed: 0.9 },
  confetti: { how: "fall", count: 12, speed: 0.35 },
  stars:    { how: "twinkle", count: 6, speed: 0.8 },
  sparkles: { how: "twinkle", count: 7, speed: 0.9 },
};

export function motionAt(motion, t) {
  let dx = 0, dy = 0, flip = false, scale = SCALE;
  if (motion === "bounce") dy = -Math.round(Math.abs(Math.sin(t * Math.PI / 0.6)) * 14);
  else if (motion === "float") dy = Math.round(Math.sin(t * 2) * 8);
  else if (motion === "sway") dx = Math.round(Math.sin(t * 2.2) * 20);
  else if (motion === "shake") { if (fmod(t, 1.6) < 0.4) dx = (Math.floor(t * 30) % 2) * 6 - 3; }
  else if (motion === "pulse") { if (fmod(t, 0.5) < 0.12) scale = 6; }
  else if (motion === "dance") { flip = Math.floor(t * 2) % 2 === 1; dy = -Math.round(Math.abs(Math.sin(t * 2 * Math.PI)) * 8); }
  return { dx, dy, flip, scale };
}

export function drawLook(ctx, recipe, t) {
  const r = cleanRecipe(recipe);
  const main = toInt(r.main), accent = toInt(r.accent), bg = toInt(r.background);
  const rect = (x, y, w, h, c) => { ctx.fillStyle = css(c); ctx.fillRect(x, y, w, h); };

  rect(0, 0, SCREEN_W, SCREEN_H, bg);

  // effects behind the character
  r.extras.forEach((name, k) => {
    const e = EFFECT[name];
    for (let i = 0; i < e.count; i++) {
      const local = t * e.speed + i / e.count;
      const round = Math.floor(local);
      const p = local - round;
      const h = mix(i + 1 + k * 31, round);
      let color = 0xFFFFFF;
      if (name === "hearts") color = (accent === 0xFFFFFF || accent === bg) ? 0xFF5FA2 : accent;
      if (name === "stars") color = bg === 0xFFE600 ? accent : 0xFFE600;
      if (name === "rain") color = 0x9FD8FF;
      if (name === "confetti") color = [main, accent, 0xFFFFFF, 0xFFE600][h % 4];
      if (light(bg) && color === 0xFFFFFF) color = OUTLINE;
      const x = 8 + (h % (SCREEN_W - 24));
      if (e.how === "twinkle") {
        const tri = p < 0.5 ? p * 2 : (1 - p) * 2;
        const n = Math.floor(tri * 3.99);
        if (n === 0) continue;
        const y = 8 + ((h >>> 12) % (SCREEN_H - 24));
        if (name === "stars" && n >= 2) drawIcon(rect, ICONS.stars, x, y, color);
        else {
          rect(x - n * 3, y, (2 * n + 1) * 3, 3, color);
          rect(x, y - n * 3, 3, (2 * n + 1) * 3, color);
        }
      } else {
        const travel = SCREEN_H + 40;
        const y = e.how === "rise" ? SCREEN_H + 10 - p * travel : -30 + p * travel;
        const wob = e.how === "rise" ? Math.round(Math.sin(t * 3 + i) * 4) : 0;
        drawIcon(rect, ICONS[name], x + wob, Math.round(y), color);
      }
    }
  });

  // the character
  const m = motionAt(r.motion, t);
  const size = N * m.scale;
  const sx = Math.floor((SCREEN_W - size) / 2) + m.dx;
  const sy = (r.text ? Math.floor((128 - size) / 2) + 4 : Math.floor((SCREEN_H - size) / 2)) + m.dy;
  if (r.character !== "none") {
    const blink = fmod(t, 3.2) < 0.15;
    drawSprite(rect, SPRITES[r.character], sx, sy, m.scale, m.flip, blink,
      { K: OUTLINE, M: main, D: shade(main, 0.72), A: accent, W: 0xFFFFFF, E: OUTLINE });
  }

  // words along the bottom
  if (r.text) drawText(ctx, r.text, t, light(bg) ? OUTLINE : 0xFFFFFF, accent === bg ? main : accent, r.character === "none");
}

function drawIcon(rect, rows, x, y, color) {
  rows.forEach((row, ry) => {
    for (let c = 0; c < row.length; c++) if (row[c] === "X") rect(x + c * U, y + ry * U, U, U, color);
  });
}

function drawSprite(rect, rows, x, y, s, flip, blink, colors) {
  for (let r = 0; r < N; r++) {
    const row = rows[r];
    let c = 0;
    while (c < N) {
      let ch = row[c];
      if (ch === ".") { c++; continue; }
      // closed eyes: top of the eye turns into skin, the bottom row into a line
      const key = (cc) => {
        let k = row[cc];
        if (blink && k === "E") k = (r + 1 < N && rows[r + 1][cc] === "E") ? "M" : "K";
        return k;
      };
      ch = key(c);
      const start = c;
      while (c < N && row[c] !== "." && key(c) === ch) c++;
      const len = c - start;
      const px = flip ? x + (N - start - len) * s : x + start * s;
      rect(px, y + r * s, len * s, s, colors[ch]);
    }
  }
}

// Text uses a 3x size of the classic 6x8 screen font. In the browser we
// imitate it with a blocky monospace font.
const TEXT_SIZE = 3;
function drawText(ctx, text, t, ink, shadow, big) {
  const size = big ? 6 : TEXT_SIZE;
  const charW = 6 * size, h = 8 * size;
  const w = text.length * charW;
  const y = big ? Math.floor((SCREEN_H - h) / 2) : 136;
  let x;
  if (w <= SCREEN_W - 16) x = Math.floor((SCREEN_W - w) / 2);
  else x = Math.floor(SCREEN_W - fmod(t * 70, SCREEN_W + w));
  ctx.font = `bold ${7 * size}px "Courier New", monospace`;
  ctx.textBaseline = "top";
  for (let i = 0; i < text.length; i++) {
    const cx = x + i * charW;
    if (cx < -charW || cx > SCREEN_W) continue;
    const bob = Math.round(Math.sin(t * 4 - i * 0.7) * 2);
    ctx.fillStyle = css(shadow);
    ctx.fillText(text[i], cx + 3, y + bob + 3);
    ctx.fillStyle = css(ink);
    ctx.fillText(text[i], cx, y + bob);
  }
}
