"""
Adds YOUR hand-drawn sprites to the training set.

1. Draw 32x32 sprites in Piskel with the "Rave Clip 32" palette (palette.gpl).
2. Export each as PNG. Name the file with what it is, like:
       sleepy-pink-bunny-with-a-crown.png
   (dashes become spaces: that's the caption the AI learns from)
3. Put them in the folder  my_drawings/  next to this file.
4. Run:  python import_drawings.py
Your drawings count 20x more than the generated ones, so the AI leans to your style.
"""
import os, json
import numpy as np
from PIL import Image
import style_engine as s

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "my_drawings")
REPEAT = 20

def nearest(rgb):
    best, bi = None, 0
    for i, c in enumerate(s.PALETTE):
        if c is None: continue
        d = sum((a - b) ** 2 for a, b in zip(rgb, ((c >> 16) & 255, (c >> 8) & 255, c & 255)))
        if best is None or d < best: best, bi = d, i
    return bi

def load(path):
    im = Image.open(path).convert("RGBA")
    if im.size != (32, 32):
        im = im.resize((32, 32), Image.NEAREST)
    px = im.load()
    return np.array([[0 if px[x, y][3] < 128 else nearest(px[x, y][:3]) for x in range(32)] for y in range(32)], dtype=np.uint8)

def main():
    files = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".png")) if os.path.isdir(SRC) else []
    if not files:
        print("No PNGs in my_drawings/ yet."); return
    grids = [load(os.path.join(SRC, f)) for f in files]
    caps = [os.path.splitext(f)[0].replace("-", " ").replace("_", " ").strip() for f in files]
    np.savez_compressed(os.path.join(HERE, "my_sprites.npz"), sprites=np.stack(grids), repeat=REPEAT)
    with open(os.path.join(HERE, "my_captions.jsonl"), "w") as f:
        for c in caps: f.write(json.dumps({"captions": [c]}) + "\n")
    print(f"Added {len(files)} of your drawings (each counts {REPEAT}x).")

if __name__ == "__main__":
    main()
