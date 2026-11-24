# Pull Alexia's own sprites out of her GIF sheets, pixel-exact (each art pixel = 6x6 block in the GIF).
# No redraw: every output pixel is copied from her art. Background color -> transparent; label digits dropped.
import sys, json; from PIL import Image, ImageSequence; import numpy as np
from scipy import ndimage
P = 6
def logical(path):
    im = Image.open(path); frames = [np.array(fr.convert("RGB"))[3::P, 3::P] for fr in ImageSequence.Iterator(im)]
    durs = [fr.info.get("duration", 110) for fr in ImageSequence.Iterator(Image.open(path))]
    return frames, durs
def slots(frames, bg, cols, rows):
    H, W = frames[0].shape[:2]; cw, rh = W // cols, H // rows; out = []
    for r in range(rows):
        for c in range(cols):
            m = np.zeros((rh, cw), bool)
            for fr in frames: m |= np.any(fr[r*rh:(r+1)*rh, c*cw:(c+1)*cw] != bg, axis=2)
            if r == 0: m[:12] = False                                         # label digits row
            lab, n = ndimage.label(m); objs = ndimage.find_objects(lab)
            big = [o for o in objs if o[0].stop - o[0].start > 15]          # drop label digits
            y0 = min(o[0].start for o in big); y1 = max(o[0].stop for o in big)
            x0 = min(o[1].start for o in big); x1 = max(o[1].stop for o in big)
            out.append((slice(r*rh+y0, r*rh+y1), slice(c*cw+x0, c*cw+x1)))
    return out
def cut(frames, bg, box):
    out = []
    for fr in frames:
        c = fr[box]; rgba = np.dstack([c, np.where(np.all(c == bg, axis=2), 0, 255)]).astype(np.uint8)
        out.append(rgba)
    return out
if __name__ == "__main__":
    outdir = sys.argv[1]; meta = {}
    for name, path, grid, labels in [
        ("mouths", "rpg_dance.gif", (5, 2), [f"{h}_mouth{i}" for h in ("straight", "curly") for i in range(1, 6)]),
        ("dances", "chunky_boots.gif", (3, 2), [f"{h}_dance{i}" for h in ("straight", "curly") for i in range(1, 4)])]:
        frames, durs = logical(path)
        vals, cnt = np.unique(frames[0].reshape(-1, 3), axis=0, return_counts=True); bg = vals[cnt.argmax()]
        bx = slots(frames, bg, *grid); assert len(bx) == len(labels), (path, len(bx))
        for lab, box in zip(labels, bx):
            fs = cut(frames, bg, box); h, w = fs[0].shape[:2]
            strip = Image.new("RGBA", (w * len(fs), h))
            for i, f in enumerate(fs): strip.paste(Image.fromarray(f), (i * w, 0))
            strip.save(f"{outdir}/{lab}.png"); meta[lab] = dict(w=w, h=h, frames=len(fs), ms=durs)
    json.dump(meta, open(f"{outdir}/sprites.json", "w"), indent=1); print(json.dumps(meta))
