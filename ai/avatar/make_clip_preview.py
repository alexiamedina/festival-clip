# Animated clip-screen preview using Alexia's own sprites (pixel-exact, integer scale).
from PIL import Image, ImageDraw, ImageFont; import json
S = 4; m = json.load(open("sprites/sprites.json"))
big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
def frames(k):
    im = Image.open(f"sprites/{k}.png"); w, h = m[k]["w"], m[k]["h"]
    return [im.crop((i*w, 0, (i+1)*w, h)).resize((w*S, h*S), Image.NEAREST) for i in range(m[k]["frames"])]
SCREENS = [("straight_dance1", "ROZ", (26,0,51), (255,225,77)), ("curly_dance2", "PLUR", (255,156,200), (255,255,255)),
           ("straight_dance3", "RAVE", (0,0,0), (125,255,200)), ("curly_mouth2", "HI!", (47,58,158), (255,255,255))]
fs = [frames(k) for k, *_ in SCREENS]
out = []
for t in range(8):
    sheet = Image.new("RGB", (2*640+3*20, 2*340+3*20), (247,238,221))
    for n, (k, word, bg, fg) in enumerate(SCREENS):
        scr = Image.new("RGB", (320,170), bg); d = ImageDraw.Draw(scr); f = fs[n][t]
        scr.paste(f, (8 + (116 - f.width)//2, 170 - f.height - 2), f)
        tw = d.textlength(word, font=big); d.text((124 + (196 - tw)/2, 54), word, fill=fg, font=big)
        x, y = 20 + (n % 2)*660, 20 + (n//2)*360
        sheet.paste(scr.resize((640,340), Image.NEAREST), (x, y))
    out.append(sheet)
out[0].save("hers/your-gif-sprites-on-clip.gif", save_all=True, append_images=out[1:], duration=120, loop=0)
# still sheet of every animation, frame 1, real size x4
keys = list(m); sheet = Image.new("RGB", (len(keys)//2*130+20, 2*170+60), (29,21,51))
for i, k in enumerate(keys):
    f = frames(k)[0]; sheet.paste(f, (20 + (i % 8)*130, 20 + (i//8)*180 + (140 - f.height)), f)
sheet.save("hers/all-your-sprites.png")
