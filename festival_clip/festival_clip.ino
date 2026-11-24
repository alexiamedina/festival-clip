// ============================================================
//  Festival hairclip  ·  LILYGO T-Display S3
//  The clip listens over Bluetooth. When your phone sends an artist
//  name, the screen switches to that artist's look. The phone can also
//  send a whole set schedule: then the clip switches by itself at the
//  right times, even while your phone is locked in your pocket.
//  When no artist is playing, it shows a sleepy bunny face that blinks.
//  NEW: the phone's on-device AI can send a custom look ("pink bunny with
//  hearts"). The drawing code for that lives in the ai_look.h tab.
//  NEWER: "scenes" = words with effects, backgrounds and mini-you
//  (scene.h tab). The pictures for it are in scene_assets.h.
//
//  Library needed: "GFX Library for Arduino" (by Moon On Our Nation)
//  Board setting:  ESP32S3 Dev Module, esp32 core 3.2.0
//  Bluetooth comes built into the esp32 core, nothing to install.
// ============================================================

#include <Arduino_GFX_Library.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLE2902.h>

// ---------- Things you can change easily ----------

// The name your phone sees when it looks for the clip.
#define CLIP_NAME "RAVE CLIP"

// Screen brightness, 1 (dim) to 16 (full). The T-Display S3 backlight chip has 16 steps.
const uint8_t BRIGHTNESS = 16;

const float SCROLL_SPEED  = 90;   // pixels per second
const float BOUNCE_HEIGHT = 8;    // how far letters bob up and down
const float BOUNCE_SPEED  = 1.6;  // bounces per second
const int   SHADOW_OFFSET = 5;    // pink shadow distance
const bool  SPARKLES_ON   = true;

// ---------- Bunny face colors (shown when no artist is playing) ----------
const uint32_t BUNNY_BG_HEX    = 0xF7EEDD;   // ivory
const uint32_t BUNNY_EYE_HEX   = 0x3B2B2E;   // dark cocoa eyes + mouth
const uint32_t BUNNY_BLUSH_HEX = 0xEBA3AE;   // dusty pink cheeks
const uint32_t BUNNY_NOSE_HEX  = 0xD9788A;   // slightly deeper pink nose
const float    BLINK_EVERY     = 4.2;        // seconds between blinks
const float    SLEEPY_EVERY    = 24;         // every 24 s she gets drowsy...
const float    SLEEPY_FOR      = 6;          // ...for 6 s, with little z's

// ---------- Artist looks ----------
// When the phone sends an artist, the clip looks for it here.
// "match" is the artist name in lowercase with no spaces or symbols
// (so "Fred again.." becomes "fredagain"). "text" is what scrolls.
// Colors are 0xRRGGBB like a web color picker: background, letters, shadow.
// Add your own lines! Artists that aren't listed still work: their
// name scrolls in a color picked just for them.

struct Look {
  const char *match;
  const char *text;
  uint32_t bg, ink, shadow;
};

const Look LOOKS[] = {
  // match          text           background  letters   shadow
  { "roz",          "ROZ",         0xFFE600,   0x000000, 0xFF2FA0 },
  { "example",      "EXAMPLE",     0x1A0033,   0x00FFD5, 0xFF00AA },
  // { "fredagain", "FRED AGAIN",  0x000000,   0xFFFFFF, 0x3D7BFF },
};
const int LOOK_COUNT = sizeof(LOOKS) / sizeof(LOOKS[0]);

// Color sets for artists that aren't in the list above.
const uint32_t SPARE_PALETTES[][3] = {
  { 0xFF6EC7, 0xFFFFFF, 0x7A00FF },   // bubblegum
  { 0x00E5FF, 0x000000, 0xFF2FA0 },   // aqua
  { 0x9DFF00, 0x000000, 0x00A2FF },   // slime
  { 0x14002B, 0xFF9CF5, 0x00FFC8 },   // night
  { 0xFF8A00, 0xFFFFFF, 0xB0005A },   // sunset
  { 0xFFFFFF, 0xFF2FA0, 0x00C2FF },   // candy
};
const int SPARE_COUNT = sizeof(SPARE_PALETTES) / sizeof(SPARE_PALETTES[0]);

// ---------- Bluetooth "address" (don't change: the app uses these) ----------
// Phone writes the artist name as plain text to ARTIST_UUID.
// Sending an empty name, or "-", goes back to the bunny face.
#define SERVICE_UUID "f3a1c0de-5a7e-4b1d-9c00-000000000001"
#define ARTIST_UUID  "f3a1c0de-5a7e-4b1d-9c00-000000000002"
// Phone writes schedule lines to SCHEDULE_UUID (see PROTOCOL.md):
//   C                      clear the schedule (auto mode off)
//   T|<now>                the time right now (seconds since 1970)
//   S|<start>|<end>|<name> one set
//   GO                     auto mode on
#define SCHEDULE_UUID "f3a1c0de-5a7e-4b1d-9c00-000000000003"
// Phone writes an AI look recipe to AI_UUID (see PROTOCOL.md):
//   bunny|FF9CC8|FFFFFF|2A0F3D|hearts|bounce|
#define AI_UUID "f3a1c0de-5a7e-4b1d-9c00-000000000004"
// Phone writes a scene line to SCENE_UUID (see PROTOCOL.md):
//   fx=invert;sp=2;st=shadow;fg=FFFFFF;ac=FF2FA0;bg=000000;b2=FF2FA0;bp=solid;av=none;t=ROZ
#define SCENE_UUID "f3a1c0de-5a7e-4b1d-9c00-000000000005"

// ---------- The RØZ letters (hand-drawn grids) ----------

const char *LETTER_R[] = {
  "...........", "XXXXXXXX...", "XXXXXXXXX..", "XXX....XXX.",
  "XXX....XXX.", "XXX....XXX.", "XXXXXXXXX..", "XXXXXXXX...",
  "XXX..XXX...", "XXX...XXX..", "XXX....XXX.", "XXX.....XXX",
  "...........",
};
const char *LETTER_O_SLASH[] = {
  "..........XX", "..XXXXXXXXX.", ".XXXXXXXXXX.", ".XXX....XXX.",
  ".XXX...XXXX.", ".XXX..XXXXX.", ".XXX.XX.XXX.", ".XXXXX..XXX.",
  ".XXXX...XXX.", ".XXX....XXX.", ".XXXXXXXXXX.", ".XXXXXXXXX..",
  "XX..........",
};
const char *LETTER_Z[] = {
  "..........", "XXXXXXXXXX", "XXXXXXXXXX", ".......XXX",
  "......XXX.", ".....XXX..", "....XXX...", "...XXX....",
  "..XXX.....", ".XXX......", "XXXXXXXXXX", "XXXXXXXXXX",
  "..........",
};
const int LETTER_ROWS = 13;
const int GRID_SCALE = 9;
const char **ROZ_WORD[] = { LETTER_R, LETTER_O_SLASH, LETTER_Z };
const int ROZ_LEN = 3;
const int LETTER_GAP = 2;

// Other artists use the screen's built-in pixel font, blown up big.
// Each letter is 6x8 font pixels, so size 11 makes letters 66x88.
const int FONT_SIZE = 11;

// ---------- Board wiring (don't change) ----------
#define PIN_POWER_ON  15
#define PIN_BACKLIGHT 38

Arduino_DataBus *bus = new Arduino_ESP32PAR8Q(
    7 /* DC */, 6 /* CS */, 8 /* WR */, 9 /* RD */,
    39, 40, 41, 42, 45, 46, 47, 48 /* D0..D7 */);

Arduino_GFX *screen = new Arduino_ST7789(
    bus, 5 /* RST */, 1 /* rotation: wide */, true /* IPS */,
    170 /* width */, 320 /* height */,
    35, 0, 35, 0 /* offsets for this screen */);

const int SCREEN_W = 320;
const int SCREEN_H = 170;
Arduino_Canvas *gfx = new Arduino_Canvas(SCREEN_W, SCREEN_H, screen);

// ---------- What's showing right now ----------

enum Mode { BUNNY, ROZ_LETTERS, TEXT, AI_LOOK, SCENE };
Mode mode = BUNNY;
char showText[41] = "";         // text to scroll in TEXT mode
uint16_t BG, INK, SHADOW, SPARK;
float lookStart = 0;            // when the current look began (for a flash)

// The Bluetooth side drops new names here, and loop() picks them up.
portMUX_TYPE inboxLock = portMUX_INITIALIZER_UNLOCKED;
char inbox[41];
volatile bool inboxFull = false;
volatile bool phoneConnected = false;
char aiInbox[121];                  // AI recipes wait here for loop()
volatile bool aiInboxFull = false;
char sceneInbox[201];               // scene lines wait here for loop()
volatile bool sceneInboxFull = false;

// ---------- The schedule (for auto mode) ----------
struct Set {
  int64_t start, end;   // seconds since 1970
  char name[41];
};
const int MAX_SETS = 80;
Set sets[MAX_SETS];
int setCount = 0;
bool autoMode = false;
int64_t clockAtSync = 0;      // phone's time when it last told us
uint32_t millisAtSync = 0;    // our own timer at that moment
char autoShowing[41] = "\x01";  // what auto mode last put on screen

int64_t nowSeconds() {
  return clockAtSync + (int64_t)((millis() - millisAtSync) / 1000);
}

// ---------- Helpers ----------

uint16_t toScreenColor(uint32_t hex) {
  uint8_t r = (hex >> 16) & 0xFF, g = (hex >> 8) & 0xFF, b = hex & 0xFF;
  return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

// Turns "Fred again.." into "fredagain" and "RØZ" into "roz",
// so small spelling differences from the schedule still match.
void makeKey(const char *in, char *out, int outSize) {
  int n = 0;
  for (int i = 0; in[i] && n < outSize - 1; i++) {
    uint8_t c = in[i];
    if (c == 0xC3 && (uint8_t)in[i + 1] != 0) {   // Ø ø é etc.
      uint8_t d = in[++i];
      char base = 0;
      if (d == 0x98 || d == 0xB8 || (d >= 0x92 && d <= 0x96) || (d >= 0xB2 && d <= 0xB6)) base = 'o';
      else if ((d >= 0x80 && d <= 0x85) || (d >= 0xA0 && d <= 0xA5)) base = 'a';
      else if ((d >= 0x88 && d <= 0x8B) || (d >= 0xA8 && d <= 0xAB)) base = 'e';
      else if ((d >= 0x8C && d <= 0x8F) || (d >= 0xAC && d <= 0xAF)) base = 'i';
      else if ((d >= 0x99 && d <= 0x9C) || (d >= 0xB9 && d <= 0xBC)) base = 'u';
      if (base) out[n++] = base;
    } else if (isalnum(c)) {
      out[n++] = tolower(c);
    }
  }
  out[n] = 0;
}

// Text the big font can draw: capitals, numbers, spaces, a few symbols.
void makeDisplayText(const char *in, char *out, int outSize) {
  int n = 0;
  for (int i = 0; in[i] && n < outSize - 1; i++) {
    uint8_t c = in[i];
    if (c == 0xC3 && in[i + 1]) {          // accented letter: use plain one
      char tmp[3] = { (char)c, in[i + 1], 0 }, k[2];
      makeKey(tmp, k, 2);
      if (k[0]) out[n++] = toupper(k[0]);
      i++;
    } else if (c >= 32 && c < 127) {
      out[n++] = toupper(c);
    }
  }
  out[n] = 0;
}

uint32_t mix(uint32_t a, uint32_t b) {
  uint32_t h = a * 2654435761u ^ b * 40503u;
  h ^= h >> 15; h *= 2246822519u; h ^= h >> 13;
  return h;
}

uint32_t hashText(const char *s) {
  uint32_t h = 2166136261u;
  while (*s) { h ^= (uint8_t)*s++; h *= 16777619u; }
  return h;
}

// Picks the look for an artist name sent by the phone.
void showArtist(const char *name) {
  char key[41];
  makeKey(name, key, sizeof(key));
  if (key[0] == 0) {                            // empty or "-" = bunny face
    mode = BUNNY;
    BG = toScreenColor(BUNNY_BG_HEX);
    INK = toScreenColor(BUNNY_EYE_HEX);
    SHADOW = toScreenColor(BUNNY_BLUSH_HEX);
    lookStart = millis() / 1000.0f;
    Serial.println("No artist: bunny face");
    return;
  }

  const Look *found = nullptr;
  for (int i = 0; i < LOOK_COUNT; i++) {
    if (strcmp(LOOKS[i].match, key) == 0) { found = &LOOKS[i]; break; }
  }

  if (found) {
    BG = toScreenColor(found->bg);
    INK = toScreenColor(found->ink);
    SHADOW = toScreenColor(found->shadow);
    strncpy(showText, found->text, sizeof(showText) - 1);
  } else {
    const uint32_t *p = SPARE_PALETTES[hashText(key) % SPARE_COUNT];
    BG = toScreenColor(p[0]);
    INK = toScreenColor(p[1]);
    SHADOW = toScreenColor(p[2]);
    makeDisplayText(name, showText, sizeof(showText));
    if (showText[0] == 0) strcpy(showText, key);
  }
  mode = (strcmp(key, "roz") == 0) ? ROZ_LETTERS : TEXT;
  lookStart = millis() / 1000.0f;

  Serial.print("Now showing: ");
  Serial.println(name);
}

// ---------- Bluetooth ----------

class ArtistWritten : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    String v = c->getValue();
    portENTER_CRITICAL(&inboxLock);
    strncpy(inbox, v.c_str(), sizeof(inbox) - 1);
    inbox[sizeof(inbox) - 1] = 0;
    inboxFull = true;
    autoMode = false;   // tapping an artist by hand turns auto mode off
    portEXIT_CRITICAL(&inboxLock);
  }
};

// Schedule lines are small, so we handle them right away.
class ScheduleWritten : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    String v = c->getValue();
    const char *line = v.c_str();
    portENTER_CRITICAL(&inboxLock);
    if (strcmp(line, "C") == 0) {
      setCount = 0;
      autoMode = false;
    } else if (strncmp(line, "T|", 2) == 0) {
      clockAtSync = strtoll(line + 2, nullptr, 10);
      millisAtSync = millis();
    } else if (strncmp(line, "S|", 2) == 0 && setCount < MAX_SETS) {
      char *p;
      Set &st = sets[setCount];
      st.start = strtoll(line + 2, &p, 10);
      if (*p == '|') {
        st.end = strtoll(p + 1, &p, 10);
        if (*p == '|') {
          strncpy(st.name, p + 1, sizeof(st.name) - 1);
          st.name[sizeof(st.name) - 1] = 0;
          setCount++;
        }
      }
    } else if (strcmp(line, "GO") == 0) {
      autoMode = true;
      autoShowing[0] = 1;   // force a refresh
    }
    portEXIT_CRITICAL(&inboxLock);
  }
};

// An AI look from the phone. Like tapping an artist, it turns auto mode off.
class AiWritten : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    String v = c->getValue();
    portENTER_CRITICAL(&inboxLock);
    strncpy(aiInbox, v.c_str(), sizeof(aiInbox) - 1);
    aiInbox[sizeof(aiInbox) - 1] = 0;
    aiInboxFull = true;
    autoMode = false;
    portEXIT_CRITICAL(&inboxLock);
  }
};

// A scene from the phone. Also turns auto mode off.
class SceneWritten : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    String v = c->getValue();
    portENTER_CRITICAL(&inboxLock);
    strncpy(sceneInbox, v.c_str(), sizeof(sceneInbox) - 1);
    sceneInbox[sizeof(sceneInbox) - 1] = 0;
    sceneInboxFull = true;
    autoMode = false;
    portEXIT_CRITICAL(&inboxLock);
  }
};

class PhoneStatus : public BLEServerCallbacks {
  void onConnect(BLEServer *s) override { phoneConnected = true; }
  void onDisconnect(BLEServer *s) override {
    phoneConnected = false;
    BLEDevice::startAdvertising();   // let the phone find us again
  }
};

void startBluetooth() {
  BLEDevice::init(CLIP_NAME);
  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new PhoneStatus());

  BLEService *service = server->createService(SERVICE_UUID);
  BLECharacteristic *artist = service->createCharacteristic(
      ARTIST_UUID,
      BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE |
      BLECharacteristic::PROPERTY_WRITE_NR);
  artist->setCallbacks(new ArtistWritten());
  artist->setValue("");
  BLECharacteristic *schedule = service->createCharacteristic(
      SCHEDULE_UUID,
      BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  schedule->setCallbacks(new ScheduleWritten());
  BLECharacteristic *aiLook = service->createCharacteristic(
      AI_UUID,
      BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  aiLook->setCallbacks(new AiWritten());
  BLECharacteristic *sceneChar = service->createCharacteristic(
      SCENE_UUID,
      BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  sceneChar->setCallbacks(new SceneWritten());
  service->start();

  BLEAdvertising *adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(SERVICE_UUID);
  adv->setScanResponse(true);
  BLEDevice::startAdvertising();
  Serial.println("Bluetooth on. Look for " CLIP_NAME " on your phone.");
}

// ---------- Drawing ----------

void drawGridLetter(const char *art[], int x, int y, uint16_t color) {
  int s = GRID_SCALE;
  for (int r = 0; r < LETTER_ROWS; r++) {
    const char *row = art[r];
    int c = 0;
    while (row[c]) {
      if (row[c] == 'X') {
        int start = c;
        while (row[c] == 'X') c++;
        gfx->fillRect(x + start * s, y + r * s, (c - start) * s, s, color);
      } else {
        c++;
      }
    }
  }
}

void drawFontLetter(char ch, int x, int y, uint16_t color) {
  gfx->setTextColor(color);
  gfx->setCursor(x, y);
  gfx->print(ch);
}

const int SPARKLE_COUNT = 7;
const float SPARKLE_TIME = 1.1;

void drawSparkles(float t) {
  const int u = 3;
  for (int i = 0; i < SPARKLE_COUNT; i++) {
    float local = t / SPARKLE_TIME + i * 0.37f;
    uint32_t round_ = (uint32_t)local;
    float p = local - round_;
    float tri = p < 0.5f ? p * 2 : (1 - p) * 2;
    int n = (int)(tri * 3.99f);
    if (n == 0) continue;
    uint32_t h = mix(i + 1, round_);
    int cx = 12 + h % (SCREEN_W - 24);
    int cy = 12 + (h >> 12) % (SCREEN_H - 24);
    gfx->fillRect(cx - n * u, cy, (2 * n + 1) * u, u, SPARK);
    gfx->fillRect(cx, cy - n * u, u, (2 * n + 1) * u, SPARK);
    if (n >= 2) gfx->fillRect(cx - u, cy - u, 3 * u, 3 * u, SPARK);
  }
}

// Tiny dot in the corner: blinks while waiting for the phone,
// stays on once the phone is connected.
void drawStatusDot(float t) {
  bool on = phoneConnected || fmodf(t, 1.0f) < 0.5f;
  if (on) gfx->fillRect(SCREEN_W - 9, 4, 5, 5, phoneConnected ? INK : SHADOW);
}

// ---------- Bunny face ----------
// Drawn on a chunky grid: every "pixel" is a 5x5 block on the screen,
// so the face looks like pixel art. The grid is 64 wide x 34 tall.
const int P = 5;
int faceDY = 0;   // whole face bobs a little

void px(int x, int y, int w, int h, uint16_t c) {
  gfx->fillRect(x * P, (y + faceDY) * P, w * P, h * P, c);
}

// A filled oval on the chunky grid.
void pxOval(int cx, int cy, int rx, int ry, uint16_t c) {
  for (int dy = -ry; dy <= ry; dy++) {
    float f = 1.0f - (float)(dy * dy) / ((ry + 0.5f) * (ry + 0.5f));
    int hw = (int)((rx + 0.5f) * sqrtf(f < 0 ? 0 : f));
    px(cx - hw, cy + dy, hw * 2 + 1, 1, c);
  }
}

// open: 1 = wide awake, 0.5 = sleepy, 0 = closed
void drawEye(int cx, int cy, float open, uint16_t eye, uint16_t bg) {
  uint16_t white = toScreenColor(0xFFFFFF);
  if (open <= 0.05f) {
    // closed: a little smile-shaped line
    px(cx - 3, cy, 1, 1, eye);
    px(cx - 2, cy + 1, 5, 1, eye);
    px(cx + 3, cy, 1, 1, eye);
    return;
  }
  pxOval(cx, cy, 3, 4, eye);
  px(cx - 2, cy - 2, 2, 2, white);   // big sparkle
  px(cx + 1, cy + 1, 1, 1, white);   // tiny sparkle
  if (open < 1.0f) {
    // eyelid comes down from the top
    int lid = (int)((1.0f - open) * 9);
    px(cx - 4, cy - 5, 9, lid, bg);
    px(cx - 3, cy - 5 + lid, 7, 1, eye);
  }
}

void drawBunny(float t) {
  uint16_t eye = toScreenColor(BUNNY_EYE_HEX);
  uint16_t blush = toScreenColor(BUNNY_BLUSH_HEX);
  uint16_t nose = toScreenColor(BUNNY_NOSE_HEX);

  gfx->fillScreen(BG);
  faceDY = (fmodf(t, 2.4f) < 1.2f) ? 0 : 1;   // slow little bob

  // How open are the eyes right now?
  float sleepyT = fmodf(t, SLEEPY_EVERY);
  bool sleepy = sleepyT > SLEEPY_EVERY - SLEEPY_FOR;
  float open = sleepy ? 0.45f : 1.0f;
  float b = fmodf(t, BLINK_EVERY);
  int blinkRound = (int)(t / BLINK_EVERY);
  if (b < 0.14f) open = 0;                                         // blink
  if (blinkRound % 3 == 2 && b > 0.28f && b < 0.42f) open = 0;     // double blink sometimes
  if (sleepy && sleepyT > SLEEPY_EVERY - 1.5f) open = 0;          // nods off at the end

  // cheeks
  pxOval(13, 21, 4, 2, blush);
  pxOval(51, 21, 4, 2, blush);
  // eyes
  drawEye(20, 15, open, eye, BG);
  drawEye(44, 15, open, eye, BG);
  // nose
  px(31, 19, 3, 1, nose);
  px(32, 20, 1, 1, eye);
  // little w mouth
  px(30, 21, 1, 1, eye);
  px(31, 22, 1, 1, eye);
  px(32, 21, 1, 1, eye);
  px(33, 22, 1, 1, eye);
  px(34, 21, 1, 1, eye);

  // floating z's while sleepy
  if (sleepy) {
    float s = sleepyT - (SLEEPY_EVERY - SLEEPY_FOR);
    for (int i = 0; i < 2; i++) {
      float zt = fmodf(s - i * 1.2f, 2.4f);
      if (s - i * 1.2f < 0) continue;
      int zx = 52 + i * 5 + (int)(zt * 2);
      int zy = 12 - (int)(zt * 5);
      int saveDY = faceDY; faceDY = 0;
      px(zx, zy, 4, 1, blush);          // a little pixel Z
      px(zx + 2, zy + 1, 1, 1, blush);
      px(zx + 1, zy + 2, 1, 1, blush);
      px(zx, zy + 3, 4, 1, blush);
      faceDY = saveDY;
    }
  }

  drawStatusDot(t);
  gfx->flush();
}

// The AI look drawing code (needs the helpers above).
#include "ai_look.h"
#include "scene.h"

void drawFrame(float t) {
  // Quick flash of the shadow color when the artist changes.
  if (t - lookStart < 0.15f) {
    gfx->fillScreen(SHADOW);
    gfx->flush();
    return;
  }

  if (mode == BUNNY) {
    drawBunny(t);
    return;
  }
  if (mode == AI_LOOK) {
    drawAiLook(t);
    return;
  }
  if (mode == SCENE) {
    drawScene(t);
    return;
  }

  gfx->fillScreen(BG);
  if (SPARKLES_ON) drawSparkles(t);

  bool useRozLetters = (mode == ROZ_LETTERS);
  int count = useRozLetters ? ROZ_LEN : strlen(showText);
  int letterH = useRozLetters ? LETTER_ROWS * GRID_SCALE : 7 * FONT_SIZE;
  int wordW = 0;
  for (int i = 0; i < count; i++) {
    wordW += useRozLetters ? (strlen(ROZ_WORD[i][0]) + LETTER_GAP) * GRID_SCALE
                           : 6 * FONT_SIZE;
  }

  float travel = SCREEN_W + wordW + SHADOW_OFFSET;
  float x = SCREEN_W - fmodf(t * SCROLL_SPEED, travel);
  int baseY = (SCREEN_H - letterH) / 2;

  for (int i = 0; i < count; i++) {
    int step = useRozLetters ? (strlen(ROZ_WORD[i][0]) + LETTER_GAP) * GRID_SCALE
                             : 6 * FONT_SIZE;
    int lx = (int)x;
    if (lx > -step && lx < SCREEN_W) {           // only draw what's on screen
      float bob = sinf(t * BOUNCE_SPEED * 2 * PI - i * 0.9f) * BOUNCE_HEIGHT;
      int ly = baseY + (int)bob;
      if (useRozLetters) {
        drawGridLetter(ROZ_WORD[i], lx + SHADOW_OFFSET, ly + SHADOW_OFFSET, SHADOW);
        drawGridLetter(ROZ_WORD[i], lx, ly, INK);
      } else {
        drawFontLetter(showText[i], lx + SHADOW_OFFSET, ly + SHADOW_OFFSET, SHADOW);
        drawFontLetter(showText[i], lx, ly, INK);
      }
    }
    x += step;
  }

  drawStatusDot(t);
  gfx->flush();
}

// ---------- Screen colors + brightness ----------

// LILYGO's own settings for this exact screen (from their T-Display-S3 factory code):
// voltages + gamma curves. The library's general ST7789 settings made colors look dark.
void useLilygoColors() {
  static const uint8_t ops[] = {
    BEGIN_WRITE,
    WRITE_C8_BYTES, 0xB2, 5, 0x0B, 0x0B, 0x00, 0x33, 0x33,
    WRITE_C8_BYTES, 0xB7, 1, 0x75,
    WRITE_C8_BYTES, 0xBB, 1, 0x28,
    WRITE_C8_BYTES, 0xC0, 1, 0x2C,
    WRITE_C8_BYTES, 0xC2, 1, 0x01,
    WRITE_C8_BYTES, 0xC3, 1, 0x1F,
    WRITE_C8_BYTES, 0xC6, 1, 0x13,
    WRITE_C8_BYTES, 0xD0, 1, 0xA7,
    WRITE_C8_BYTES, 0xD0, 2, 0xA4, 0xA1,
    WRITE_C8_BYTES, 0xD6, 1, 0xA1,
    WRITE_C8_BYTES, 0xE0, 14, 0xF0, 0x05, 0x0A, 0x06, 0x06, 0x03, 0x2B, 0x32, 0x43, 0x36, 0x11, 0x10, 0x2B, 0x32,
    WRITE_C8_BYTES, 0xE1, 14, 0xF0, 0x08, 0x0C, 0x0B, 0x09, 0x24, 0x2B, 0x22, 0x43, 0x38, 0x15, 0x16, 0x2F, 0x37,
    END_WRITE,
  };
  bus->batchOperation(ops, sizeof(ops));
}

// The backlight chip doesn't understand dimming signals (that made it dark).
// It counts quick off-on pulses instead: each pulse is one step dimmer. (Same as LILYGO's code.)
void setBrightness(uint8_t level) {
  static uint8_t now = 0;
  if (level > 16) level = 16;
  if (level == 0) { digitalWrite(PIN_BACKLIGHT, LOW); delay(3); now = 0; return; }
  if (now == 0) { digitalWrite(PIN_BACKLIGHT, HIGH); now = 16; delayMicroseconds(30); }
  int pulses = (16 + (16 - level) - (16 - now)) % 16;
  for (int i = 0; i < pulses; i++) { digitalWrite(PIN_BACKLIGHT, LOW); digitalWrite(PIN_BACKLIGHT, HIGH); }
  now = level;
}

// ---------- Arduino start + loop ----------

void setup() {
  Serial.begin(115200);

  pinMode(PIN_POWER_ON, OUTPUT);
  digitalWrite(PIN_POWER_ON, HIGH);

  SPARK = toScreenColor(0xFFFFFF);
  showArtist("");
  lookStart = -1;   // no flash on startup

  if (!gfx->begin()) {
    Serial.println("Screen didn't start. Check the board setting.");
  }
  gfx->setTextSize(FONT_SIZE);
  gfx->setTextWrap(false);

  useLilygoColors();
  pinMode(PIN_BACKLIGHT, OUTPUT);
  setBrightness(BRIGHTNESS);

  startBluetooth();
}

void loop() {
  if (inboxFull) {
    char name[41];
    portENTER_CRITICAL(&inboxLock);
    strcpy(name, inbox);
    inboxFull = false;
    portEXIT_CRITICAL(&inboxLock);
    showArtist(name);
  }

  if (aiInboxFull) {
    char line[121];
    portENTER_CRITICAL(&inboxLock);
    strcpy(line, aiInbox);
    aiInboxFull = false;
    portEXIT_CRITICAL(&inboxLock);
    if (parseAiLook(line)) {
      mode = AI_LOOK;
      SHADOW = toScreenColor(ai.accent);   // color of the quick flash
      INK = toScreenColor(ai.main);        // color of the status dot
      autoShowing[0] = 1;
      lookStart = millis() / 1000.0f;
      Serial.print("AI look: ");
      Serial.println(line);
    }
  }

  if (sceneInboxFull) {
    char line[201];
    portENTER_CRITICAL(&inboxLock);
    strcpy(line, sceneInbox);
    sceneInboxFull = false;
    portEXIT_CRITICAL(&inboxLock);
    if (parseScene(line)) {
      mode = SCENE;
      SHADOW = toScreenColor(scene.ac);
      INK = toScreenColor(scene.fg);
      lookStart = millis() / 1000.0f;
      Serial.print("Scene: ");
      Serial.println(line);
    }
  }

  // Auto mode: twice a second, check who's playing right now.
  static uint32_t lastCheck = 0;
  if (millis() - lastCheck > 500) {
    lastCheck = millis();
    char playing[41] = "";
    bool on;
    portENTER_CRITICAL(&inboxLock);
    on = autoMode;
    if (on) {
      int64_t now = nowSeconds();
      for (int i = 0; i < setCount; i++) {
        if (now >= sets[i].start && now < sets[i].end) {
          strcpy(playing, sets[i].name);
          break;
        }
      }
    }
    portEXIT_CRITICAL(&inboxLock);
    if (on && strcmp(playing, autoShowing) != 0) {
      strcpy(autoShowing, playing);
      showArtist(playing);   // "" = nobody on = bunny face
    }
  }
  drawFrame(millis() / 1000.0f);
}
