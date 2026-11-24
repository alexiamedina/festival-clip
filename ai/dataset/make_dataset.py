"""
Builds the training set for the pixel AI.
Output (in this folder):
  sprites.npz      all sprites as numbers (each pixel = palette index 0-31)
  captions.jsonl   for each sprite, a few ways to describe it
  palette.gpl      the 32 colors, for Piskel / Aseprite
  preview.png      a sample sheet with captions, to check by eye
Run:  python make_dataset.py
"""
import json, random, os
import numpy as np
from PIL import Image, ImageDraw
import style_engine as s

random.seed(7)
HERE = os.path.dirname(os.path.abspath(__file__))

EXPR_WORDS = {"happy": ["happy", "smiling", "cute", ""], "sleepy": ["sleepy", "tired", "sleeping"], "wink": ["winking"],
              "crying": ["crying", "sad"], "angry": ["angry", "grumpy", "mad"], "surprised": ["surprised", "shocked"],
              "in love": ["lovestruck", "in love", "heart-eyed"]}
COLOR_WORDS = {h: [h] for h in s.HUES}
COLOR_WORDS.update({"hot pink": ["hot pink", "magenta"], "lavender": ["lavender", "lilac", "pastel purple"],
                    "mint": ["mint", "mint green", "pastel green"], "grey": ["grey", "gray"], "cream": ["cream", "beige"],
                    "blue": ["blue", "sky blue"], "pink": ["pink", "baby pink", "pastel pink"]})

def caption(subject, main, expr, acc):
    noun = random.choice(s.SUBJECTS[subject][1])
    color = random.choice(COLOR_WORDS[main])
    if main == s.NATURAL[subject] and random.random() < 0.5:
        color = ""                       # "a cat" = the usual orange cat
    e = random.choice(EXPR_WORDS[expr])
    if expr == "in love" and e == "in love":
        words = " ".join(w for w in (color, noun) if w) + " in love"
    elif expr == "in love" and e == "heart-eyed" and random.random() < 0.5:
        words = " ".join(w for w in (color, noun) if w) + " with heart eyes"
    else:
        words = " ".join(w for w in (e, color, noun) if w)
    if acc != "none":
        words += random.choice([" with ", " wearing "]) + random.choice(s.ACC_WORDS[acc])
    if random.random() < 0.3:
        lead = random.choice(["a", "a cute", "pixel art of a", "kawaii"])
        if lead.endswith(" a") or lead == "a":
            if words[0] in "aeiou": lead += "n"
        words = lead + " " + words
    return words.strip().replace("  ", " ")

def main():
    grids, caps, meta = [], [], []
    for subject in s.SUBJECTS:
        # Subjects without a drawn face only get "happy" and no face accessories,
        # so captions never promise something the picture doesn't show.
        has_face = s.SUBJECTS[subject][0](s.Grid()).face
        exprs = s.EXPRESSIONS if has_face else ["happy"]
        accs = s.ACCESSORIES if has_face else [a for a in s.ACCESSORIES if a not in ("sunglasses", "headphones")]
        for main in s.HUES:
            for expr in exprs:
                for acc in accs:
                    if acc == "sunglasses" and expr not in ("happy", "angry"):
                        continue   # glasses would hide the eyes the caption talks about
                    grids.append(np.array(s.draw(subject, main, expr, acc), dtype=np.uint8))
                    caps.append([caption(subject, main, expr, acc) for _ in range(3)])
                    meta.append({"subject": subject, "color": main, "expression": expr, "accessory": acc})
    arr = np.stack(grids)
    np.savez_compressed(os.path.join(HERE, "sprites.npz"), sprites=arr)
    with open(os.path.join(HERE, "captions.jsonl"), "w") as f:
        for c, m in zip(caps, meta):
            f.write(json.dumps({"captions": c, **m}) + "\n")
    # Piskel/Aseprite palette
    with open(os.path.join(HERE, "palette.gpl"), "w") as f:
        f.write("GIMP Palette\nName: Rave Clip 32\nColumns: 8\n#\n")
        names = ["empty", "outline"] + [f"{h}{' shade' if i else ''}" for h in s.HUES for i in (0, 1)]
        for c, n in zip(s.PALETTE, names):
            c = c if c is not None else 0xFFFFFF
            f.write(f"{(c >> 16) & 255:3d} {(c >> 8) & 255:3d} {c & 255:3d}\t{n}\n")
    # preview sheet: 48 random sprites with one caption each
    pick = random.sample(range(len(arr)), 48)
    S, cols, cw, ch = 4, 8, 32 * 4 + 40, 32 * 4 + 46
    sheet = Image.new("RGBA", (cols * cw, 6 * ch), (42, 15, 61, 255))
    d = ImageDraw.Draw(sheet)
    for k, i in enumerate(pick):
        x, y = (k % cols) * cw, (k // cols) * ch
        sheet.alpha_composite(s.to_image(arr[i].tolist(), S), (x + 20, y + 6))
        text = caps[i][0]
        if len(text) > 26: text = text[:25] + "…"
        d.text((x + 6, y + 32 * S + 12), text, fill=(247, 238, 221, 255))
    sheet.save(os.path.join(HERE, "preview.png"))
    print(f"{len(arr)} sprites, {arr.nbytes / 1e6:.1f} MB raw")

if __name__ == "__main__":
    main()
