// ============================================================
//  Scene engine: words with effects + a background + mini-Alexia.
//  The phone sends one line like:
//    fx=invert;sp=2;st=shadow;fg=FFFFFF;ac=FF2FA0;bg=000000;b2=FF2FA0;bp=solid;av=none;hr=curly;t=ROZ
//  The app has the same drawing code (web-app/scene.js) for its preview.
//  If you change one, change the other.
// ============================================================
#pragma once
#include "scene_assets.h"

enum SceneFx { FX_STILL, FX_SCROLL, FX_WAVE, FX_BOUNCE, FX_INVERT, FX_RAINBOW, FX_GLITCH, FX_TYPE, FX_PULSE };
const char *const FX_NAMES[] = { "still", "scroll", "wave", "bounce", "invert", "rainbow", "glitch", "type", "pulse" };
enum SceneStyle { ST_PLAIN, ST_SHADOW, ST_OUTLINE };
const char *const STYLE_NAMES[] = { "plain", "shadow", "outline" };
enum SceneBg { BP_SOLID, BP_GRADIENT, BP_CHECKER, BP_STRIPES, BP_DOTS, BP_STARS, BP_HEARTS, BP_SPARKLES, BP_RAINBOW };
const char *const BG_NAMES[] = { "solid", "gradient", "checker", "stripes", "dots", "stars", "hearts", "sparkles", "rainbow" };
enum SceneMove { MV_NONE, MV_SMILE, MV_TEETH, MV_OOH, MV_GRIN, MV_CHILL, MV_DANCE1, MV_DANCE2, MV_DANCE3 };
const char *const MOVE_NAMES[] = { "none", "smile", "teeth", "ooh", "grin", "chill", "dance1", "dance2", "dance3" };
// older names from saved scenes still work
const char *const OLD_MOVE_NAMES[] = { "none", "idle", "x", "kiss", "x", "x", "dance", "jump", "squat" };
enum SceneHair { HR_STRAIGHT, HR_CURLY };
const char *const HAIR_NAMES[] = { "straight", "curly" };

const float SCENE_RATES[] = { 0.6f, 1.0f, 1.6f };
const int FLASH_HZ[] = { 1, 2, 3 };   // invert: never more than 3 flashes a second (seizure safety)

struct Scene {
  int fx, sp, st, bp, av, hr;
  uint32_t fg, ac, bg, b2;
  char t[25];
};
Scene scene;

// ---------- reading the line ----------
static int pickName(const char *v, const char *const *names, int count, int fallback) {
  for (int i = 0; i < count; i++) if (strcmp(v, names[i]) == 0) return i;
  return fallback;
}
static uint32_t sceneHex(const char *s, uint32_t fallback) {
  if (strlen(s) != 6) return fallback;
  char *end;
  uint32_t v = strtoul(s, &end, 16);
  return *end ? fallback : v;
}

bool parseScene(const char *line) {
  Scene s = { FX_STILL, 2, ST_SHADOW, BP_SOLID, MV_NONE, HR_CURLY, 0xFFFFFF, 0xFF2FA0, 0x1A0033, 0xFF2FA0, "" };
  const char *p = line;
  while (*p) {
    if (p[0] == 't' && p[1] == '=') {          // the text is always last
      strncpy(s.t, p + 2, sizeof(s.t) - 1);
      s.t[sizeof(s.t) - 1] = 0;
      break;
    }
    char key[4] = "", val[12] = "";
    int k = 0, v = 0;
    while (*p && *p != '=' && *p != ';') { if (k < 3) key[k++] = *p; p++; }
    key[k] = 0;
    if (*p == '=') p++;
    while (*p && *p != ';') { if (v < 11) val[v++] = *p; p++; }
    val[v] = 0;
    if (*p == ';') p++;
    if (!strcmp(key, "fx")) s.fx = pickName(val, FX_NAMES, 9, FX_STILL);
    else if (!strcmp(key, "sp")) { int n = atoi(val); s.sp = (n >= 1 && n <= 3) ? n : 2; }
    else if (!strcmp(key, "st")) s.st = pickName(val, STYLE_NAMES, 3, ST_SHADOW);
    else if (!strcmp(key, "bp")) s.bp = pickName(val, BG_NAMES, 9, BP_SOLID);
    else if (!strcmp(key, "av")) s.av = pickName(val, MOVE_NAMES, 9, pickName(val, OLD_MOVE_NAMES, 9, MV_NONE));
    else if (!strcmp(key, "hr")) s.hr = pickName(val, HAIR_NAMES, 2, HR_CURLY);
    else if (!strcmp(key, "fg")) s.fg = sceneHex(val, s.fg);
    else if (!strcmp(key, "ac")) s.ac = sceneHex(val, s.ac);
    else if (!strcmp(key, "bg")) s.bg = sceneHex(val, s.bg);
    else if (!strcmp(key, "b2")) s.b2 = sceneHex(val, s.b2);
  }
  scene = s;
  return true;
}

// ---------- helpers ----------
static float sFmod(float a, float b) { return a - b * floorf(a / b); }
static void sRect(int x, int y, int w, int h, uint32_t c) { gfx->fillRect(x, y, w, h, toScreenColor(c)); }

uint32_t hueColor(int h) {
  h = ((h % 360) + 360) % 360;
  int region = h / 60, f = ((h % 60) * 255) / 60, q = 255 - f;
  int r, g, b;
  switch (region) {
    case 0: r = 255; g = f; b = 0; break;
    case 1: r = q; g = 255; b = 0; break;
    case 2: r = 0; g = 255; b = f; break;
    case 3: r = 0; g = q; b = 255; break;
    case 4: r = f; g = 0; b = 255; break;
    default: r = 255; g = 0; b = q; break;
  }
  return (r << 16) | (g << 8) | b;
}
static uint32_t sLerp(uint32_t a, uint32_t b, int k, int n) {
  uint32_t out = 0;
  for (int s = 16; s >= 0; s -= 8) {
    uint32_t ch = (((a >> s) & 255) * (n - k) + ((b >> s) & 255) * k) / n;
    out |= ch << s;
  }
  return out;
}

// ---------- background ----------
static void drawSceneBackground(float t, float rate) {
  uint32_t bg = scene.bg, b2 = scene.b2;
  int bp = scene.bp;
  if (bp == BP_GRADIENT) {
    for (int k = 0; k < 10; k++) sRect(0, k * 17, SCREEN_W, 17, sLerp(bg, b2, k, 9));
    return;
  }
  if (bp == BP_RAINBOW) {
    int shift = (int)floorf(t * 60 * rate);
    for (int k = 0; k < 16; k++) sRect(k * 20, 0, 20, SCREEN_H, hueColor(k * 22 + shift));
    return;
  }
  sRect(0, 0, SCREEN_W, SCREEN_H, bg);
  if (bp == BP_CHECKER) {
    int off = ((int)floorf(t * 10 * rate)) % 40;
    for (int y = 0; y < SCREEN_H; y += 20)
      for (int x = -off; x < SCREEN_W; x += 20)
        if (((((x + off) / 20) + y / 20) & 1) == 0) sRect(x, y, 20, 20, b2);
  } else if (bp == BP_STRIPES) {
    int off = (int)floorf(t * 20 * rate);
    for (int y = 0; y < SCREEN_H; y++) {
      int start = (y + off) % 28;
      for (int x = -start; x < SCREEN_W; x += 28) sRect(x, y, 14, 1, b2);
    }
  } else if (bp == BP_DOTS) {
    int off = ((int)floorf(t * 8 * rate)) % 24;
    int row = 0;
    for (int y = 4; y < SCREEN_H; y += 24, row++)
      for (int x = -off + (row % 2) * 12; x < SCREEN_W; x += 24) sRect(x, y, 8, 8, b2);
  } else if (bp == BP_STARS || bp == BP_SPARKLES) {
    int count = bp == BP_STARS ? 10 : 14;
    for (int i = 0; i < count; i++) {
      float local = t * 0.9f * rate + i * 0.37f;
      uint32_t round_ = (uint32_t)floorf(local);
      float p = local - round_;
      float tri = p < 0.5f ? p * 2 : (1 - p) * 2;
      int n = (int)(tri * 3.99f);
      if (n == 0) continue;
      uint32_t h = mix(i + 1, round_);
      int x = 8 + h % (SCREEN_W - 16), y = 8 + (h >> 12) % (SCREEN_H - 16);
      int u = bp == BP_STARS ? 3 : 2;
      sRect(x - n * u, y, (2 * n + 1) * u, u, b2);
      sRect(x, y - n * u, u, (2 * n + 1) * u, b2);
      if (bp == BP_STARS && n >= 2) sRect(x - u, y - u, 3 * u, 3 * u, b2);
    }
  } else if (bp == BP_HEARTS) {
    static const char *const HEART[] = { "XX.XX", "XXXXX", "XXXXX", ".XXX.", "..X.." };
    for (int i = 0; i < 8; i++) {
      float local = t * 0.25f * rate + i / 8.0f;
      uint32_t round_ = (uint32_t)floorf(local);
      float p = local - round_;
      uint32_t h = mix(i + 1, round_);
      int x = 4 + h % (SCREEN_W - 24) + (int)roundf(sinf(t * 2 + i) * 4);
      int y = (int)roundf(SCREEN_H + 10 - p * (SCREEN_H + 40));
      for (int ry = 0; ry < 5; ry++)
        for (int c = 0; c < 5; c++)
          if (HEART[ry][c] == 'X') sRect(x + c * 4, y + ry * 4, 4, 4, b2);
    }
  }
}

// ---------- words ----------
static void sceneChar(char ch, int x, int y, int size, uint32_t color) {
  if (ch < 32 || ch > 126) return;
  const uint8_t *cols = SCENE_FONT + (ch - 32) * 5;
  for (int col = 0; col < 5; col++) {
    uint8_t bits = cols[col];
    int row = 0;
    while (row < 8) {
      if (bits & (1 << row)) {
        int start = row;
        while (row < 8 && (bits & (1 << row))) row++;
        sRect(x + col * size, y + start * size, size, (row - start) * size, color);
      } else row++;
    }
  }
}

static void sceneStyledChar(char ch, int x, int y, int size, uint32_t color, uint32_t accent) {
  int o = size / 2 > 2 ? size / 2 : 2;
  if (scene.st == ST_SHADOW) sceneChar(ch, x + o, y + o, size, accent);
  else if (scene.st == ST_OUTLINE) {
    const int d[8][2] = { {-1,0},{1,0},{0,-1},{0,1},{-1,-1},{1,-1},{-1,1},{1,1} };
    for (int i = 0; i < 8; i++) sceneChar(ch, x + d[i][0] * o, y + d[i][1] * o, size, accent);
  }
  sceneChar(ch, x, y, size, color);
}

static void drawSceneWords(float t, float rate, uint32_t fg, uint32_t ac, int rx, int rw) {
  const char *text = scene.t;
  int n = strlen(text);
  int maxSize = (int)floorf(SCREEN_H * 0.62f / 8);
  int size = (rw - 16) / (6 * n);
  if (size > maxSize) size = maxSize;
  int fx = scene.fx;
  if (size < 4 && !(fx == FX_INVERT || fx == FX_RAINBOW || fx == FX_GLITCH)) fx = FX_SCROLL;
  if (fx == FX_SCROLL || size < 4) {
    int want = scene.av != MV_NONE ? 9 : 12;
    size = want < maxSize ? want : maxSize;
  }
  if (fx == FX_PULSE && sFmod(t * 2 * rate, 1) < 0.15f) size += 1;
  int w = n * 6 * size - size, h = 7 * size;
  int x = rx + (int)floorf((rw - w) / 2.0f);
  int y0 = (SCREEN_H - h) / 2;
  if (fx == FX_SCROLL || (size >= 4 && w > rw && fx != FX_TYPE)) {
    x = rx + rw - (int)floorf(sFmod(t * 80 * rate, rw + w + 20));
  }
  int shown = n;
  if (fx == FX_TYPE) {
    shown = (int)floorf(sFmod(t * 6 * rate, n + 6));
    if (shown > n) shown = n;
  }
  int gdx = 0;
  if (fx == FX_GLITCH) {
    uint32_t g = mix((uint32_t)floorf(t * 8 * rate), 7);
    if (g % 3 == 0) gdx = (int)((g >> 4) % 5) - 2;
  }
  for (int i = 0; i < shown; i++) {
    int cx = x + i * 6 * size;
    if (cx < rx - 6 * size - 20 || cx > rx + rw + 20) continue;
    int dy = 0;
    uint32_t color = fg;
    if (fx == FX_WAVE) dy = (int)roundf(sinf(t * 4 * rate - i * 0.8f) * size);
    if (fx == FX_BOUNCE) dy = -(int)roundf(fabsf(sinf(t * PI * 1.6f * rate)) * size * 2);
    if (fx == FX_RAINBOW) color = hueColor((int)floorf(t * 120 * rate) + i * 40);
    if (fx == FX_GLITCH && gdx != 0) {
      sceneChar(text[i], cx + gdx * size, y0 + dy, size, 0xFF2FA0);
      sceneChar(text[i], cx - gdx * size, y0 + dy, size, 0x00E5FF);
    }
    sceneStyledChar(text[i], cx, y0 + dy, size, color, ac);
  }
  if (fx == FX_TYPE && sFmod(t * 2, 1) < 0.5f) sRect(x + shown * 6 * size, y0, size * 4, h, ac);
}

// ---------- mini-me ----------
const int AV_SCALE = 4;
const int AV_FPS = 9;          // her GIFs run at about 110 ms a frame
static void drawSceneAvatar(float t, float rate, int x, int y) {
  int frame = ((int)floorf(t * AV_FPS * rate)) % AVATAR_NFRAMES;
  int pic = AVATAR_ANIMS[scene.hr * 8 + scene.av - 1][frame];
  uint32_t i = AVATAR_RLE_START[pic], end = AVATAR_RLE_START[pic + 1];
  int c = 0, r = 0;
  while (i < end) {
    int n = AVATAR_RLE[i], v = AVATAR_RLE[i + 1];
    i += 2;
    if (v) sRect(x + c * AV_SCALE, y + r * AV_SCALE, n * AV_SCALE, AV_SCALE, AVATAR_PALETTE[v]);
    c += n;
    if (c >= AVATAR_W) { c = 0; r++; }
  }
}

void drawScene(float t) {
  float rate = SCENE_RATES[scene.sp - 1];
  uint32_t fg = scene.fg, ac = scene.ac;
  bool inverted = scene.fx == FX_INVERT && ((int)floorf(t * 2 * FLASH_HZ[scene.sp - 1])) % 2 == 1;
  if (inverted) {
    sRect(0, 0, SCREEN_W, SCREEN_H, fg);
    fg = scene.bg;
  } else {
    drawSceneBackground(t, rate);
  }
  int rx = 0, rw = SCREEN_W;
  if (scene.av != MV_NONE) {
    drawSceneAvatar(t, rate, 4, SCREEN_H - AVATAR_H * AV_SCALE - 2);
    rx = 8 + AVATAR_W * AV_SCALE; rw = SCREEN_W - rx - 4;
  }
  if (scene.t[0]) drawSceneWords(t, rate, fg, ac, rx, rw);
  drawStatusDot(t);
  gfx->flush();
}
