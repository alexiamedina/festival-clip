// ============================================================
//  AI looks: the phone's on-device AI turns words like
//  "pink bunny with hearts" into a short recipe line:
//     bunny|FF9CC8|FFFFFF|2A0F3D|hearts|bounce|
//  (character | main | accent | background | effects | motion | text)
//  This file draws that recipe. The phone app has the same drawing code
//  (web-app/looks.js) for its preview, so what you see is what you get.
// ============================================================
#pragma once
#include "sprites.h"

const int AI_N = 24;          // sprites are 24 x 24
const int AI_SCALE = 5;       // each sprite pixel = 5 x 5 screen pixels
const int AI_U = 4;           // effect pixel size
const uint32_t AI_OUTLINE = 0x2B1B2E;

enum AiMotion { M_BOUNCE, M_FLOAT, M_SWAY, M_SHAKE, M_PULSE, M_DANCE };
const char *const MOTION_NAMES[] = { "bounce", "float", "sway", "shake", "pulse", "dance" };

enum AiExtra { X_HEARTS, X_SPARKLES, X_STARS, X_BUBBLES, X_NOTES, X_RAIN, X_CONFETTI, X_ZZZ };
const char *const EXTRA_NAMES[] = { "hearts", "sparkles", "stars", "bubbles", "notes", "rain", "confetti", "zzz" };
const int EXTRA_KINDS = 8;

struct AiLook {
  int sprite;              // index into SPRITES, or -1 for "none"
  uint32_t main, accent, bg;
  int extras[3];
  int extraCount;
  int motion;
  char text[17];
};
AiLook ai;

// ---------- reading the recipe line ----------

// Copies the next "|"-separated piece of *p into out, and moves *p past it.
static void nextField(const char **p, char *out, int outSize) {
  int n = 0;
  while (**p && **p != '|') {
    if (n < outSize - 1) out[n++] = **p;
    (*p)++;
  }
  out[n] = 0;
  if (**p == '|') (*p)++;
}

static uint32_t hexOr(const char *s, uint32_t fallback) {
  if (strlen(s) != 6) return fallback;
  char *end;
  uint32_t v = strtoul(s, &end, 16);
  return *end ? fallback : v;
}

// Returns false if the line doesn't look like a recipe.
bool parseAiLook(const char *line) {
  char f[48];
  const char *p = line;
  AiLook r;

  nextField(&p, f, sizeof(f));
  r.sprite = -1;
  for (int i = 0; i < SPRITE_COUNT; i++) {
    if (strcmp(SPRITES[i].name, f) == 0) { r.sprite = i; break; }
  }
  if (r.sprite < 0 && strcmp(f, "none") != 0) r.sprite = 0;   // unknown = bunny

  nextField(&p, f, sizeof(f)); r.main = hexOr(f, 0xFF9CC8);
  nextField(&p, f, sizeof(f)); r.accent = hexOr(f, 0xFFFFFF);
  nextField(&p, f, sizeof(f)); r.bg = hexOr(f, 0x1A0033);

  nextField(&p, f, sizeof(f));     // effects, comma separated
  r.extraCount = 0;
  char *save = nullptr;
  for (char *e = strtok_r(f, ",", &save); e && r.extraCount < 3; e = strtok_r(nullptr, ",", &save)) {
    for (int k = 0; k < EXTRA_KINDS; k++) {
      if (strcmp(EXTRA_NAMES[k], e) == 0) { r.extras[r.extraCount++] = k; break; }
    }
  }

  nextField(&p, f, sizeof(f));
  r.motion = M_BOUNCE;
  for (int m = 0; m < 6; m++) if (strcmp(MOTION_NAMES[m], f) == 0) r.motion = m;

  nextField(&p, r.text, sizeof(r.text));
  ai = r;
  return true;
}

// ---------- drawing ----------

static uint32_t aiShade(uint32_t c, float f) {
  uint32_t r = ((c >> 16) & 255) * f, g = ((c >> 8) & 255) * f, b = (c & 255) * f;
  return (r << 16) | (g << 8) | b;
}
static bool aiLight(uint32_t c) {
  return ((c >> 16) & 255) * 3 + ((c >> 8) & 255) * 6 + (c & 255) > 1400;
}
static float aiFmod(float a, float b) { return a - b * floorf(a / b); }

const char *const ICON_HEART[] = { "XX.XX", "XXXXX", "XXXXX", ".XXX.", "..X.." };
const char *const ICON_STAR[]  = { "..X..", ".XXX.", "XXXXX", ".XXX.", ".X.X." };
const char *const ICON_NOTE[]  = { "..XX", "..XX", "..X.", "..X.", "XXX.", "XXX." };
const char *const ICON_BUBBLE[] = { ".XX.", "X..X", "X..X", ".XX." };
const char *const ICON_Z[]     = { "XXXX", "..X.", ".X..", "XXXX" };
const char *const ICON_DROP[]  = { "X", "X", "X" };
const char *const ICON_DOT[]   = { "XX", "XX" };

struct Effect { const char *const *icon; int rows; char how; int count; float speed; };
// how: 'r' rise, 'f' fall, 't' twinkle
const Effect EFFECTS[] = {
  { ICON_HEART,  5, 'r', 6,  0.25f },   // hearts
  { nullptr,     0, 't', 7,  0.9f  },   // sparkles
  { ICON_STAR,   5, 't', 6,  0.8f  },   // stars
  { ICON_BUBBLE, 4, 'r', 6,  0.3f  },   // bubbles
  { ICON_NOTE,   6, 'r', 5,  0.3f  },   // notes
  { ICON_DROP,   3, 'f', 10, 0.9f  },   // rain
  { ICON_DOT,    2, 'f', 12, 0.35f },   // confetti
  { ICON_Z,      4, 'r', 3,  0.2f  },   // zzz
};

static void drawIcon(const char *const *rows, int count, int x, int y, uint16_t color) {
  for (int r = 0; r < count; r++) {
    for (int c = 0; rows[r][c]; c++) {
      if (rows[r][c] == 'X') gfx->fillRect(x + c * AI_U, y + r * AI_U, AI_U, AI_U, color);
    }
  }
}

static void drawEffects(float t) {
  for (int k = 0; k < ai.extraCount; k++) {
    int kind = ai.extras[k];
    const Effect &e = EFFECTS[kind];
    for (int i = 0; i < e.count; i++) {
      float local = t * e.speed + (float)i / e.count;
      uint32_t round_ = (uint32_t)floorf(local);
      float p = local - round_;
      uint32_t h = mix(i + 1 + k * 31, round_);
      uint32_t color = 0xFFFFFF;
      if (kind == X_HEARTS) color = (ai.accent == 0xFFFFFF || ai.accent == ai.bg) ? 0xFF5FA2 : ai.accent;
      if (kind == X_STARS) color = ai.bg == 0xFFE600 ? ai.accent : 0xFFE600;
      if (kind == X_RAIN) color = 0x9FD8FF;
      if (kind == X_CONFETTI) {
        const uint32_t pick[] = { ai.main, ai.accent, 0xFFFFFF, 0xFFE600 };
        color = pick[h % 4];
      }
      if (aiLight(ai.bg) && color == 0xFFFFFF) color = AI_OUTLINE;
      uint16_t c = toScreenColor(color);
      int x = 8 + h % (SCREEN_W - 24);

      if (e.how == 't') {
        float tri = p < 0.5f ? p * 2 : (1 - p) * 2;
        int n = (int)(tri * 3.99f);
        if (n == 0) continue;
        int y = 8 + (h >> 12) % (SCREEN_H - 24);
        if (kind == X_STARS && n >= 2) {
          drawIcon(ICON_STAR, 5, x, y, c);
        } else {
          gfx->fillRect(x - n * 3, y, (2 * n + 1) * 3, 3, c);
          gfx->fillRect(x, y - n * 3, 3, (2 * n + 1) * 3, c);
        }
      } else {
        float travel = SCREEN_H + 40;
        float y = e.how == 'r' ? SCREEN_H + 10 - p * travel : -30 + p * travel;
        int wob = e.how == 'r' ? (int)roundf(sinf(t * 3 + i) * 4) : 0;
        drawIcon(e.icon, e.rows, x + wob, (int)roundf(y), c);
      }
    }
  }
}

static char spriteKey(const char *const *rows, int r, int c, bool blink) {
  char k = rows[r][c];
  if (blink && k == 'E') k = (r + 1 < AI_N && rows[r + 1][c] == 'E') ? 'M' : 'K';
  return k;
}

static void drawSprite(const char *const *rows, int x, int y, int s, bool flip, bool blink) {
  uint16_t K = toScreenColor(AI_OUTLINE), M = toScreenColor(ai.main);
  uint16_t D = toScreenColor(aiShade(ai.main, 0.72f)), A = toScreenColor(ai.accent);
  uint16_t W = toScreenColor(0xFFFFFF);
  for (int r = 0; r < AI_N; r++) {
    int c = 0;
    while (c < AI_N) {
      if (rows[r][c] == '.') { c++; continue; }
      char ch = spriteKey(rows, r, c, blink);
      int start = c;
      while (c < AI_N && rows[r][c] != '.' && spriteKey(rows, r, c, blink) == ch) c++;
      int len = c - start;
      uint16_t col = ch == 'M' ? M : ch == 'D' ? D : ch == 'A' ? A : ch == 'W' ? W : K;
      int px_ = flip ? x + (AI_N - start - len) * s : x + start * s;
      gfx->fillRect(px_, y + r * s, len * s, s, col);
    }
  }
}

static void drawAiText(float t) {
  bool big = ai.sprite < 0;
  int size = big ? 6 : 3;
  int len = strlen(ai.text);
  int charW = 6 * size, h = 8 * size;
  int w = len * charW;
  int y = big ? (SCREEN_H - h) / 2 : 136;
  int x;
  if (w <= SCREEN_W - 16) x = (SCREEN_W - w) / 2;
  else x = (int)floorf(SCREEN_W - aiFmod(t * 70, SCREEN_W + w));
  uint16_t ink = toScreenColor(aiLight(ai.bg) ? AI_OUTLINE : 0xFFFFFF);
  uint16_t shadow = toScreenColor(ai.accent == ai.bg ? ai.main : ai.accent);
  gfx->setTextSize(size);
  for (int i = 0; i < len; i++) {
    int cx = x + i * charW;
    if (cx < -charW || cx > SCREEN_W) continue;
    int bob = (int)roundf(sinf(t * 4 - i * 0.7f) * 2);
    drawFontLetter(ai.text[i], cx + 3, y + bob + 3, shadow);
    drawFontLetter(ai.text[i], cx, y + bob, ink);
  }
  gfx->setTextSize(FONT_SIZE);   // put the artist-name size back
}

void drawAiLook(float t) {
  gfx->fillScreen(toScreenColor(ai.bg));
  drawEffects(t);

  int dx = 0, dy = 0, s = AI_SCALE;
  bool flip = false;
  switch (ai.motion) {
    case M_BOUNCE: dy = -(int)roundf(fabsf(sinf(t * PI / 0.6f)) * 14); break;
    case M_FLOAT:  dy = (int)roundf(sinf(t * 2) * 8); break;
    case M_SWAY:   dx = (int)roundf(sinf(t * 2.2f) * 20); break;
    case M_SHAKE:  if (aiFmod(t, 1.6f) < 0.4f) dx = ((int)floorf(t * 30) % 2) * 6 - 3; break;
    case M_PULSE:  if (aiFmod(t, 0.5f) < 0.12f) s = 6; break;
    case M_DANCE:
      flip = ((int)floorf(t * 2)) % 2 == 1;
      dy = -(int)roundf(fabsf(sinf(t * 2 * PI)) * 8);
      break;
  }

  if (ai.sprite >= 0) {
    int size = AI_N * s;
    int sx = (SCREEN_W - size) / 2 + dx;
    int sy = (ai.text[0] ? (128 - size) / 2 + 4 : (SCREEN_H - size) / 2) + dy;
    bool blink = aiFmod(t, 3.2f) < 0.15f;
    drawSprite(SPRITES[ai.sprite].rows, sx, sy, s, flip, blink);
  }
  if (ai.text[0]) drawAiText(t);

  drawStatusDot(t);
  gfx->flush();
}
