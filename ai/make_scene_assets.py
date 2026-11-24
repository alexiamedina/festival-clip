"""
Makes the shared pictures for the scene engine, in two copies that match:
  festival_clip/scene_assets.h   (for the clip)
  web-app/scene-assets.js        (for the app preview)
- FONT: the classic 5x7 screen font (from Adafruit GFX, BSD license), letters 32-126
- AVATAR: Alexia's own retro sprites from her GIFs (ai/avatar/sprites), pixel-exact,
  straight + curly hair, 5 faces + 3 dances, 8 frames each, run-length encoded.
Run:  python make_scene_assets.py
"""
import os, re, json
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

# ---- font ----
src = open(os.path.join(HERE, "assets", "glcdfont.h")).read()
body = src[src.index("{") + 1: src.index("}")]
nums = [int(x, 16) for x in re.findall(r"0x[0-9A-Fa-f]{2}", body)]
font = nums[32 * 5: 127 * 5]
assert len(font) == 95 * 5

# ---- avatar: Alexia's own GIF sprites (avatar/sprites, made by avatar/extract_gif_sprites.py) ----
# Every pixel is copied from her art. Frames share one box (bottom-centered) and are stored
# run-length encoded: pairs of (run, color number), runs never cross a row. Color 0 = see-through.
SP = os.path.join(HERE, "avatar", "sprites")
meta = json.load(open(os.path.join(SP, "sprites.json")))
HAIRS = ["straight", "curly"]
MOVES = ["smile", "teeth", "ooh", "grin", "chill", "dance1", "dance2", "dance3"]
SRC = {"smile": "mouth1", "teeth": "mouth2", "ooh": "mouth3", "grin": "mouth4", "chill": "mouth5",
       "dance1": "dance1", "dance2": "dance2", "dance3": "dance3"}
NF = 8
AW = max(v["w"] for v in meta.values()); AH = max(v["h"] for v in meta.values())
palette, uniq, rle, anims = [], {}, [], []
for h in HAIRS:
    for mv in MOVES:
        key = f"{h}_{SRC[mv]}"; v = meta[key]; assert v["frames"] == NF
        strip = Image.open(os.path.join(SP, key + ".png")).convert("RGBA"); px = strip.load()
        ox, oy = (AW - v["w"]) // 2, AH - v["h"]
        seq = []
        for f in range(NF):
            grid = [[0] * AW for _ in range(AH)]
            for y in range(v["h"]):
                for x in range(v["w"]):
                    r, g, b, al = px[f * v["w"] + x, y]
                    if al < 128: continue
                    c = (r << 16) | (g << 8) | b
                    if c not in palette: palette.append(c)
                    grid[oy + y][ox + x] = palette.index(c) + 1
            k = tuple(map(tuple, grid))
            if k not in uniq:
                uniq[k] = len(rle); data = []
                for row in grid:
                    x = 0
                    while x < AW:
                        c0 = row[x]; n = 1
                        while x + n < AW and row[x + n] == c0: n += 1
                        data += [n, c0]; x += n
                rle.append(data)
            seq.append(uniq[k])
        anims.append(seq)
assert len(palette) < 255
offs, flat = [], []
for d in rle: offs.append(len(flat)); flat += d
offs.append(len(flat))

# ---- write C header ----
c = ["// Made by ai/make_scene_assets.py. Don't edit by hand.", "#pragma once", "#include <stdint.h>", "",
     "// Classic 5x7 font (Adafruit GFX, BSD license), characters 32..126, 5 columns each, bit 0 = top row",
     "const uint8_t SCENE_FONT[] = {"]
for i in range(0, len(font), 15):
    c.append("  " + ", ".join(f"0x{v:02X}" for v in font[i:i + 15]) + ",")
c += ["};", "", "// Mini-Alexia: her own pixel sprites (2 hairstyles x 8 moves x 8 frames)",
      f"const int AVATAR_W = {AW}, AVATAR_H = {AH}, AVATAR_NFRAMES = {NF};",
      f"const uint32_t AVATAR_PALETTE[{len(palette) + 1}] = {{ 0, " + ", ".join(f"0x{v:06X}" for v in palette) + " };",
      f"const uint32_t AVATAR_RLE_START[{len(offs)}] = {{ " + ", ".join(map(str, offs)) + " };",
      f"const uint8_t AVATAR_RLE[{len(flat)}] = {{"]
for i in range(0, len(flat), 40): c.append("  " + ",".join(map(str, flat[i:i + 40])) + ",")
c += ["};", f"// AVATAR_ANIMS[hair * {len(MOVES)} + move][frame] = picture number",
      f"const uint8_t AVATAR_ANIMS[{len(anims)}][{NF}] = {{"]
c += ["  { " + ", ".join(map(str, sq)) + " }," for sq in anims]
c += ["};"]
open(os.path.join(ROOT, "festival_clip", "scene_assets.h"), "w").write("\n".join(c) + "\n")

# ---- write JS module ----
js = ["// Made by ai/make_scene_assets.py. Same data as the clip's scene_assets.h.",
      f"export const FONT = {json.dumps(font)};",
      f"export const AVATAR_W = {AW}, AVATAR_H = {AH}, AVATAR_NFRAMES = {NF};",
      f"export const AVATAR_PALETTE = {json.dumps([0] + palette)};",
      f"export const HAIRS = {json.dumps(HAIRS)};",
      f"export const AV_MOVES = {json.dumps(MOVES)};",
      f"export const AVATAR_RLE_START = {json.dumps(offs)};",
      "export const AVATAR_RLE = " + json.dumps(flat, separators=(",", ":")) + ";",
      "export const AVATAR_ANIMS = " + json.dumps(anims, separators=(",", ":")) + ";"]
open(os.path.join(ROOT, "web-app", "scene-assets.js"), "w").write("\n".join(js) + "\n")
print(f"font ok, avatar {AW}x{AH}, {len(palette)} colors, {len(rle)} pictures, {len(flat)} RLE bytes")
