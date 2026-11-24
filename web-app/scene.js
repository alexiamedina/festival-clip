// The scene engine: words with effects, a background, and mini-Alexia.
// This is the app's copy for the live preview. The clip's copy is
// festival_clip/scene.h and draws the exact same pixels. Change both together.
//
// A scene travels over Bluetooth as one line of key=value pairs:
//   fx=invert;sp=2;st=shadow;fg=FFFFFF;ac=FF2FA0;bg=000000;b2=FF2FA0;bp=solid;av=none;hr=curly;t=ROZ
// (t, the text, always goes last.)

import { FONT, AVATAR_W, AVATAR_H, AVATAR_NFRAMES, AVATAR_PALETTE, AVATAR_RLE_START, AVATAR_RLE, AVATAR_ANIMS } from "./scene-assets.js";

export const SCREEN_W = 320, SCREEN_H = 170;
export const EFFECTS = ["still", "scroll", "wave", "bounce", "invert", "rainbow", "glitch", "type", "pulse"];
export const STYLES = ["plain", "shadow", "outline"];
export const BACKGROUNDS = ["solid", "gradient", "checker", "stripes", "dots", "stars", "hearts", "sparkles", "rainbow"];
export const MOVES = ["none", "smile", "teeth", "ooh", "grin", "chill", "dance1", "dance2", "dance3"];
export const HAIRS = ["straight", "curly"];
const OLD_MOVES = { idle: "smile", kiss: "ooh", dance: "dance1", jump: "dance2", squat: "dance3" };
export const MAX_TEXT = 24;
const RATES = [0.6, 1, 1.6];
const FLASH_HZ = [1, 2, 3];   // invert: never more than 3 flashes a second (seizure safety)

export const DEFAULT_SCENE = {
  fx: "still", sp: 2, st: "shadow", fg: "FFFFFF", ac: "FF2FA0", bg: "1A0033", b2: "FF2FA0",
  bp: "solid", av: "none", hr: "curly", t: "ROZ",
};

// ---------- scene <-> line ----------
const hex = (v, d) => (/^[0-9A-Fa-f]{6}$/.test(String(v || "")) ? String(v).toUpperCase() : d);

export function cleanScene(s = {}) {
  const d = DEFAULT_SCENE;
  return {
    fx: EFFECTS.includes(s.fx) ? s.fx : d.fx,
    sp: [1, 2, 3].includes(Number(s.sp)) ? Number(s.sp) : d.sp,
    st: STYLES.includes(s.st) ? s.st : d.st,
    fg: hex(s.fg, d.fg), ac: hex(s.ac, d.ac), bg: hex(s.bg, d.bg), b2: hex(s.b2, d.b2),
    bp: BACKGROUNDS.includes(s.bp) ? s.bp : d.bp,
    av: MOVES.includes(s.av) ? s.av : (OLD_MOVES[s.av] ?? d.av),
    hr: HAIRS.includes(s.hr) ? s.hr : d.hr,
    t: String(s.t ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[Øø]/g, "O")
      .replace(/[^ -~]/g, "").replace(/[;|]/g, "").slice(0, MAX_TEXT),
  };
}

export function sceneToLine(s) {
  const c = cleanScene(s);
  return `fx=${c.fx};sp=${c.sp};st=${c.st};fg=${c.fg};ac=${c.ac};bg=${c.bg};b2=${c.b2};bp=${c.bp};av=${c.av};hr=${c.hr};t=${c.t}`;
}

export function lineToScene(line) {
  const out = {};
  const ti = line.indexOf("t=");
  const head = ti >= 0 && (ti === 0 || line[ti - 1] === ";") ? line.slice(0, ti) : line;
  if (ti >= 0) out.t = line.slice(ti + 2);
  for (const part of head.split(";")) {
    const eq = part.indexOf("=");
    if (eq > 0) out[part.slice(0, eq)] = part.slice(eq + 1);
  }
  return cleanScene(out);
}

// ---------- small helpers (same math as the clip) ----------
const toInt = (h) => parseInt(h, 16);
const css = (n) => "#" + (n >>> 0).toString(16).padStart(6, "0").slice(-6);
const fmod = (a, b) => a - b * Math.floor(a / b);
function mix(a, b) {
  let h = (Math.imul(a, 2654435761) ^ Math.imul(b, 40503)) >>> 0;
  h = (h ^ (h >>> 15)) >>> 0;
  h = Math.imul(h, 2246822519) >>> 0;
  return (h ^ (h >>> 13)) >>> 0;
}
export function hue(h) {           // h 0..359 -> bright color
  h = ((h % 360) + 360) % 360;
  const region = Math.floor(h / 60), f = Math.floor(((h % 60) * 255) / 60);
  const q = 255 - f;
  const rgb = [[255, f, 0], [q, 255, 0], [0, 255, f], [0, q, 255], [f, 0, 255], [255, 0, q]][region];
  return (rgb[0] << 16) | (rgb[1] << 8) | rgb[2];
}
function lerp(a, b, k, n) {       // color k/n of the way from a to b
  const ch = (s) => Math.floor((((a >> s) & 255) * (n - k) + ((b >> s) & 255) * k) / n);
  return (ch(16) << 16) | (ch(8) << 8) | ch(0);
}

// ---------- drawing ----------
export function drawScene(ctx, scene, t) {
  const s = cleanScene(scene);
  const rect = (x, y, w, h, c) => { ctx.fillStyle = css(c); ctx.fillRect(x, y, w, h); };
  let fg = toInt(s.fg), ac = toInt(s.ac), bg = toInt(s.bg), b2 = toInt(s.b2);
  const rate = RATES[s.sp - 1];

  // invert: swap text and background colors, at most 3 times a second
  const inverted = s.fx === "invert" && Math.floor(t * 2 * FLASH_HZ[s.sp - 1]) % 2 === 1;
  if (inverted) {
    rect(0, 0, SCREEN_W, SCREEN_H, fg);
    [fg, bg] = [bg, fg];
  } else {
    drawBackground(rect, s.bp, bg, b2, t, rate);
  }

  // mini-me on the left, words on the right
  let rx = 0, rw = SCREEN_W;
  if (s.av !== "none") {
    drawAvatar(rect, s, t, rate, 4, SCREEN_H - AVATAR_H * AV_SCALE - 2);
    rx = 8 + AVATAR_W * AV_SCALE; rw = SCREEN_W - rx - 4;
  }
  if (s.t) drawWords(rect, s, t, rate, fg, ac, inverted ? fg : bg, rx, rw);
}

function drawBackground(rect, bp, bg, b2, t, rate) {
  if (bp === "gradient") {
    for (let k = 0; k < 10; k++) rect(0, k * 17, SCREEN_W, 17, lerp(bg, b2, k, 9));
    return;
  }
  if (bp === "rainbow") {
    const shift = Math.floor(t * 60 * rate);
    for (let k = 0; k < 16; k++) rect(k * 20, 0, 20, SCREEN_H, hue(k * 22 + shift));
    return;
  }
  rect(0, 0, SCREEN_W, SCREEN_H, bg);
  if (bp === "checker") {
    const off = Math.floor(t * 10 * rate) % 40;
    for (let y = 0; y < SCREEN_H; y += 20)
      for (let x = -off; x < SCREEN_W; x += 20)
        if (((Math.floor((x + off) / 20) + y / 20) & 1) === 0) rect(x, y, 20, 20, b2);
  } else if (bp === "stripes") {
    const off = Math.floor(t * 20 * rate);
    for (let y = 0; y < SCREEN_H; y++) {
      const start = (y + off) % 28;
      for (let x = -start; x < SCREEN_W; x += 28) rect(x, y, 14, 1, b2);
    }
  } else if (bp === "dots") {
    const off = Math.floor(t * 8 * rate) % 24;
    for (let row = 0, y = 4; y < SCREEN_H; y += 24, row++)
      for (let x = -off + (row % 2) * 12; x < SCREEN_W; x += 24) rect(x, y, 8, 8, b2);
  } else if (bp === "stars" || bp === "sparkles") {
    const count = bp === "stars" ? 10 : 14;
    for (let i = 0; i < count; i++) {
      const local = t * 0.9 * rate + i * 0.37;
      const round = Math.floor(local);
      const p = local - round;
      const tri = p < 0.5 ? p * 2 : (1 - p) * 2;
      const n = Math.floor(tri * 3.99);
      if (n === 0) continue;
      const h = mix(i + 1, round);
      const x = 8 + (h % (SCREEN_W - 16)), y = 8 + ((h >>> 12) % (SCREEN_H - 16));
      const u = bp === "stars" ? 3 : 2;
      rect(x - n * u, y, (2 * n + 1) * u, u, b2);
      rect(x, y - n * u, u, (2 * n + 1) * u, b2);
      if (bp === "stars" && n >= 2) rect(x - u, y - u, 3 * u, 3 * u, b2);
    }
  } else if (bp === "hearts") {
    const HEART = ["XX.XX", "XXXXX", "XXXXX", ".XXX.", "..X.."];
    for (let i = 0; i < 8; i++) {
      const local = t * 0.25 * rate + i / 8;
      const round = Math.floor(local);
      const p = local - round;
      const h = mix(i + 1, round);
      const x = 4 + (h % (SCREEN_W - 24)) + Math.round(Math.sin(t * 2 + i) * 4);
      const y = Math.round(SCREEN_H + 10 - p * (SCREEN_H + 40));
      HEART.forEach((r, ry) => { for (let c = 0; c < 5; c++) if (r[c] === "X") rect(x + c * 4, y + ry * 4, 4, 4, b2); });
    }
  }
}

// Classic 5x7 font, each font pixel = size x size screen pixels.
function drawChar(rect, ch, x, y, size, color) {
  const code = ch.charCodeAt(0);
  if (code < 32 || code > 126) return;
  const base = (code - 32) * 5;
  for (let col = 0; col < 5; col++) {
    const bits = FONT[base + col];
    let row = 0;
    while (row < 8) {
      if (bits & (1 << row)) {
        const start = row;
        while (row < 8 && (bits & (1 << row))) row++;
        rect(x + col * size, y + start * size, size, (row - start) * size, color);
      } else row++;
    }
  }
}

function drawStyledChar(rect, ch, x, y, size, color, accent, style) {
  const o = Math.max(2, Math.floor(size / 2));
  if (style === "shadow") drawChar(rect, ch, x + o, y + o, size, accent);
  else if (style === "outline") {
    for (const [dx, dy] of [[-o, 0], [o, 0], [0, -o], [0, o], [-o, -o], [o, -o], [-o, o], [o, o]])
      drawChar(rect, ch, x + dx, y + dy, size, accent);
  }
  drawChar(rect, ch, x, y, size, color);
}

function drawWords(rect, s, t, rate, fg, ac, bg, rx, rw) {
  const text = s.t;
  const n = text.length;
  const maxSize = Math.floor((SCREEN_H * 0.62) / 8);          // 13
  let size = Math.min(maxSize, Math.floor((rw - 16) / (6 * n)));
  let fx = s.fx;
  if (size < 4) { fx = fx === "invert" || fx === "rainbow" || fx === "glitch" ? fx : "scroll"; }
  if (fx === "scroll" || size < 4) size = Math.min(maxSize, s.av !== "none" ? 9 : 12);
  if (fx === "pulse" && fmod(t * 2 * rate, 1) < 0.15) size += 1;
  const w = n * 6 * size - size, h = 7 * size;
  let x = rx + Math.floor((rw - w) / 2);
  const y0 = Math.floor((SCREEN_H - h) / 2);
  if (fx === "scroll" || (size >= 4 && w > rw && fx !== "type")) {
    x = rx + rw - Math.floor(fmod(t * 80 * rate, rw + w + 20));
  }
  let shown = n;
  if (fx === "type") shown = Math.min(n, Math.floor(fmod(t * 6 * rate, n + 6)));
  let gdx = 0;
  if (fx === "glitch") {
    const g = mix(Math.floor(t * 8 * rate), 7);
    if (g % 3 === 0) gdx = ((g >>> 4) % 5) - 2;
  }
  for (let i = 0; i < shown; i++) {
    const cx = x + i * 6 * size;
    if (cx < rx - 6 * size - 20 || cx > rx + rw + 20) continue;
    let dy = 0, color = fg;
    if (fx === "wave") dy = Math.round(Math.sin(t * 4 * rate - i * 0.8) * size);
    if (fx === "bounce") dy = -Math.round(Math.abs(Math.sin(t * Math.PI * 1.6 * rate)) * size * 2);
    if (fx === "rainbow") color = hue(Math.floor(t * 120 * rate) + i * 40);
    if (fx === "glitch" && gdx !== 0) {
      drawChar(rect, text[i], cx + gdx * size, y0 + dy, size, 0xFF2FA0);
      drawChar(rect, text[i], cx - gdx * size, y0 + dy, size, 0x00E5FF);
    }
    drawStyledChar(rect, text[i], cx, y0 + dy, size, color, ac, s.st);
  }
  if (fx === "type" && fmod(t * 2, 1) < 0.5) {
    rect(x + shown * 6 * size, y0, size * 4, h, ac);
  }
}

// ---------- mini-me ----------
const AV_SCALE = 4;
const AV_FPS = 9;   // her GIFs run at about 110 ms a frame
function drawAvatar(rect, s, t, rate, x, y) {
  const frame = Math.floor(t * AV_FPS * rate) % AVATAR_NFRAMES;
  const pic = AVATAR_ANIMS[HAIRS.indexOf(s.hr) * 8 + MOVES.indexOf(s.av) - 1][frame];
  let i = AVATAR_RLE_START[pic], c = 0, r = 0;
  const end = AVATAR_RLE_START[pic + 1];
  while (i < end) {
    const n = AVATAR_RLE[i], v = AVATAR_RLE[i + 1];
    i += 2;
    if (v) rect(x + c * AV_SCALE, y + r * AV_SCALE, n * AV_SCALE, AV_SCALE, AVATAR_PALETTE[v]);
    c += n;
    if (c >= AVATAR_W) { c = 0; r++; }
  }
}
