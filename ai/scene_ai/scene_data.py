"""
Makes practice examples for Alexia's scene AI: a sentence someone might type,
and the scene the clip should show for it.

  "ROZ invert colors fast"  ->  fx=invert sp=3 ... t=ROZ
  "pink bubble letters saying PLUR on a starry night with me dancing"
                            ->  fx=still st=outline fg=FF9CC8 bp=stars av=dance1 t=PLUR

Every example also marks WHICH WORDS go on the screen (the AI learns to pick them out).
The answer fields match the clip's scene line exactly (see PROTOCOL.md).
"""
import random, json

# ---------- what the clip can do (same lists as web-app/scene.js) ----------
FIELDS = {
    "fx": ["still", "scroll", "wave", "bounce", "invert", "rainbow", "glitch", "type", "pulse"],
    "sp": ["1", "2", "3"],
    "st": ["plain", "shadow", "outline"],
    "bp": ["solid", "gradient", "checker", "stripes", "dots", "stars", "hearts", "sparkles", "rainbow"],
    "av": ["none", "smile", "teeth", "ooh", "grin", "chill", "dance1", "dance2", "dance3"],
    "hr": ["straight", "curly"],
    "fg": ["FFFFFF", "000000", "1A0033", "3B2B2E", "F7EEDD", "FF9CC8", "FF2FA0", "FF4A55", "FF9A3C",
           "FFE14D", "8FE36B", "7DFFC8", "5AA8FF", "2F3A9E", "A06BFF", "C9B5FF"],
}
for k in ("ac", "bg", "b2"): FIELDS[k] = FIELDS["fg"]
FIELD_ORDER = ["fx", "sp", "st", "bp", "av", "hr", "fg", "ac", "bg", "b2"]
DEFAULT = dict(fx="still", sp="2", st="shadow", bp="solid", av="none", hr="curly",
               fg="FFFFFF", ac="FF2FA0", bg="1A0033", b2="FF9CC8")

# color words -> the 16 colors the app has
COLORS = {
    "FFFFFF": ["white", "snow white", "bright white"],
    "000000": ["black", "jet black", "pitch black"],
    "1A0033": ["dark purple", "midnight", "deep purple", "midnight purple"],
    "3B2B2E": ["dark brown", "chocolate", "espresso", "charcoal"],
    "F7EEDD": ["cream", "beige", "off white", "vanilla"],
    "FF9CC8": ["pink", "baby pink", "light pink", "pastel pink", "bubblegum"],
    "FF2FA0": ["hot pink", "magenta", "neon pink", "fuchsia"],
    "FF4A55": ["red", "cherry red", "strawberry"],
    "FF9A3C": ["orange", "tangerine", "peach"],
    "FFE14D": ["yellow", "gold", "golden", "lemon", "sunshine yellow"],
    "8FE36B": ["green", "lime", "lime green", "neon green", "slime green"],
    "7DFFC8": ["mint", "teal", "aqua", "seafoam", "turquoise"],
    "5AA8FF": ["blue", "baby blue", "sky blue", "light blue"],
    "2F3A9E": ["navy", "dark blue", "royal blue", "indigo"],
    "A06BFF": ["purple", "violet", "grape", "neon purple"],
    "C9B5FF": ["lavender", "lilac", "pastel purple", "periwinkle"],
}
DARK = {"000000", "1A0033", "3B2B2E", "2F3A9E"}

FX_WORDS = {
    "still": ["still", "not moving", "static", "standing still", "no movement", "just sitting there"],
    "scroll": ["scrolling", "scroll across", "sliding across", "moving across the screen", "like a ticker", "scroll"],
    "wave": ["wavy", "waving", "wave", "wiggly", "wiggling", "like a wave"],
    "bounce": ["bouncing", "bouncy", "bounce", "hopping", "jumping letters", "boing"],
    "invert": ["invert colors", "inverting", "flash", "flashing", "strobe", "invert", "flip the colors", "inverted flashing"],
    "rainbow": ["rainbow letters", "rainbow text", "color changing", "changing colors", "rainbow words", "multicolor letters"],
    "glitch": ["glitchy", "glitch", "glitching", "corrupted", "distorted", "broken signal"],
    "type": ["typewriter", "typing", "type it out", "letter by letter", "typed out", "being typed"],
    "pulse": ["pulsing", "pulse", "beating", "throbbing", "heartbeat", "thumping to the bass"],
}
SP_WORDS = {
    "1": ["slow", "slowly", "super slow", "chill speed", "gently", "lazy", "nice and slow"],
    "2": ["medium speed", "normal speed", "regular speed"],
    "3": ["fast", "quick", "quickly", "super fast", "really fast", "hyper", "crazy fast", "speedy"],
}
ST_WORDS = {
    "plain": ["plain letters", "simple font", "no shadow", "plain text", "flat letters"],
    "shadow": ["with a shadow", "drop shadow", "shadowed letters", "with shadows", "3d letters"],
    "outline": ["bubble letters", "outlined", "outline", "bubble font", "outlined letters", "puffy letters"],
}
BP_WORDS = {
    "solid": ["plain background", "solid background", "simple background", "solid color background"],
    "gradient": ["gradient", "fade", "ombre", "gradient background", "fading background"],
    "checker": ["checkered", "checkerboard", "checks", "checker pattern", "checkered background"],
    "stripes": ["stripes", "striped", "stripey background", "striped background"],
    "dots": ["polka dots", "dots", "dotted", "spots", "polka dot background"],
    "stars": ["stars", "starry", "night sky", "starry sky", "starry background"],
    "hearts": ["hearts", "hearts everywhere", "floating hearts", "lots of hearts", "heart background"],
    "sparkles": ["sparkles", "glitter", "sparkly", "twinkles", "sparkly background", "glittery"],
    "rainbow": ["rainbow background", "rainbow bg", "rainbow behind it", "rainbow sky"],
}
AV_WORDS = {
    "smile": ["me smiling", "mini me smiling", "my avatar smiling", "little me with a smile", "me with a cute smile"],
    "teeth": ["me with bunny teeth", "mini me showing my teeth", "me with my teeth out", "my avatar with bunny teeth"],
    "ooh": ["me making an ooh face", "mini me going ooh", "me blowing a kiss", "my avatar with a kissy face", "me surprised"],
    "grin": ["me grinning", "mini me with a big smile", "me super happy", "my avatar grinning", "me laughing"],
    "chill": ["me chilling", "mini me looking chill", "me with a chill face", "my avatar just vibing", "me unbothered"],
    "dance1": ["me dancing", "mini me dancing", "my avatar dancing", "me doing dance 1", "me doing the first dance",
               "little me dancing", "me grooving"],
    "dance2": ["me doing dance 2", "mini me doing the second dance", "me doing dance two", "my avatar doing dance 2",
               "me shuffling"],
    "dance3": ["me doing dance 3", "mini me doing the third dance", "me doing dance three", "my avatar doing dance 3",
               "me jumping around"],
}
HR_WORDS = {
    "straight": ["straight hair", "my straight hair", "sleek hair", "hair down straight"],
    "curly": ["curly hair", "my curls", "curly", "my curly hair"],
}
AV_PREFIX = ["with", "and", "plus", "", "featuring"]

# vibes set a whole look (colors + effect + background) unless you say otherwise
VIBES = [
    (["cute", "kawaii", "sweet", "girly", "soft"], dict(fg="FFFFFF", ac="FF2FA0", bg="FF9CC8", b2="FFFFFF", bp="hearts", st="outline", fx="bounce")),
    (["spooky", "creepy", "halloween", "goth", "dark"], dict(fg="FF9A3C", ac="000000", bg="000000", b2="A06BFF", bp="stars", st="shadow", fx="glitch")),
    (["techno", "underground", "warehouse", "industrial"], dict(fg="7DFFC8", ac="FF2FA0", bg="000000", b2="2F3A9E", bp="stripes", st="plain", fx="glitch")),
    (["rave", "neon", "edm", "festival", "party"], dict(fg="8FE36B", ac="FF2FA0", bg="000000", b2="FF2FA0", bp="checker", st="shadow", fx="rainbow")),
    (["ocean", "beach", "underwater", "sea"], dict(fg="FFFFFF", ac="2F3A9E", bg="5AA8FF", b2="7DFFC8", bp="dots", st="shadow", fx="wave")),
    (["sunset", "summer", "tropical", "warm"], dict(fg="FFE14D", ac="FF2FA0", bg="FF9A3C", b2="FF2FA0", bp="gradient", st="shadow", fx="wave")),
    (["galaxy", "space", "cosmic", "dreamy"], dict(fg="C9B5FF", ac="A06BFF", bg="1A0033", b2="FFFFFF", bp="stars", st="shadow", fx="pulse")),
    (["romantic", "lovey", "valentine", "in love"], dict(fg="FFFFFF", ac="FF4A55", bg="FF2FA0", b2="FF9CC8", bp="hearts", st="outline", fx="pulse")),
    (["angel", "heavenly", "pure", "clean"], dict(fg="FFFFFF", ac="C9B5FF", bg="5AA8FF", b2="FFFFFF", bp="sparkles", st="outline", fx="still")),
    (["cozy", "autumn", "fall", "coffee"], dict(fg="F7EEDD", ac="3B2B2E", bg="3B2B2E", b2="FF9A3C", bp="dots", st="shadow", fx="still")),
    (["icy", "winter", "frozen", "snowy"], dict(fg="FFFFFF", ac="5AA8FF", bg="2F3A9E", b2="FFFFFF", bp="sparkles", st="outline", fx="still")),
    (["cyber", "y2k", "futuristic", "hacker"], dict(fg="7DFFC8", ac="A06BFF", bg="000000", b2="7DFFC8", bp="checker", st="plain", fx="type")),
    (["hype", "crazy", "wild", "chaotic"], dict(fg="FFE14D", ac="FF2FA0", bg="000000", b2="FFE14D", bp="rainbow", st="shadow", fx="invert", sp="3")),
    (["chill", "lowkey", "mellow", "calm"], dict(fg="C9B5FF", ac="1A0033", bg="1A0033", b2="A06BFF", bp="gradient", st="shadow", fx="wave", sp="1")),
]
VIBE_FORMS = ["{v} vibes", "make it {v}", "{v} vibe", "something {v}", "{v} style", "very {v}", "{v}"]

# words people put on their clip
TEXTS = ["ROZ", "PLUR", "I LOVE ROZ", "HI", "HI!", "XOXO", "RAVE", "TECHNO", "BASS", "DROP IT", "KANDI KID",
         "PEACE", "LOVE", "UNITY", "RESPECT", "LETS GO", "NO SLEEP", "HUG ME", "FREE HUGS", "TRADE KANDI",
         "BASS FACE", "HOUSE MUSIC", "DNB", "DUBSTEP", "TRANCE", "EDC", "PLUR 4 LIFE", "ALEXIA", "BESTIE",
         "WHERE MY FRIENDS", "FIND ME", "LOST", "SOBER RAVER", "HYDRATE", "BPM", "WUBS", "HEADBANG", "SLAY",
         "OMG", "LOL", "YAY", "WOW", "BOOM", "VIBES", "GOOD VIBES", "STAY WEIRD", "BE KIND", "2026", "ROZ ROZ",
         "SKRILLEX", "ODESZA", "ILLENIUM", "ZEDD", "DEADMAU5", "FRED AGAIN", "PEGGY GOU", "FISHER", "JOHN SUMMIT",
         "MAU P", "SARA LANDRY", "INDIRA", "CHRIS LAKE", "ALISON WONDER", "KAYTRANADA", "GRIZ", "SUBTRONICS",
         "LEVEL UP", "SVDDEN DEATH", "EXCISION", "SEVEN LIONS", "GORGON CITY", "DOM DOLLA", "TIESTO", "MARSHMELLO"]
SYL = ["ka", "zo", "ri", "ma", "lu", "ne", "vo", "ta", "shi", "ro", "xa", "bel", "ny", "dee", "jo", "ki", "ra", "sol"]

def random_text(rng):
    r = rng.random()
    if r < 0.55: t = rng.choice(TEXTS)
    elif r < 0.8:   # made-up names, so it learns ANY word can be shown
        t = "".join(rng.choice(SYL) for _ in range(rng.randint(1, 3)))
        if rng.random() < 0.3: t += " " + "".join(rng.choice(SYL) for _ in range(rng.randint(1, 2)))
    elif r < 0.9: t = str(rng.choice([2026, 4, 69, 420, 777, 100, 24, 7]))
    else: t = rng.choice(TEXTS) + " " + rng.choice(["4EVER", "!!", "<3", "XO", "2026"])
    case = rng.random()
    if case < 0.6: t = t.upper()
    elif case < 0.85: t = t.lower()
    else: t = t.title()
    return t[:24].strip()

def text_phrase(rng, t):
    """Returns (words, which ones are the text)."""
    tw = t.split()
    form = rng.random()
    def mk(before, quote=False, after=()):
        words = list(before)
        qw = list(tw)
        if quote:
            q = rng.choice(['"', '"', "'"])
            qw[0] = q + qw[0]; qw[-1] = qw[-1] + q
        tags = [0] * len(words) + [1] * len(qw)
        words += qw
        words += list(after); tags += [0] * len(after)
        return words, tags
    if form < 0.2: return mk([], quote=rng.random() < 0.3)                                  # ROZ ...
    if form < 0.35: return mk(rng.choice([["saying"], ["that", "says"], ["that", "said"]]), quote=rng.random() < 0.5)
    if form < 0.5: return mk(rng.choice([["the", "word"], ["the", "words"], ["write"], ["text"], ["show"], ["put"]]), quote=rng.random() < 0.5)
    if form < 0.65: return mk([], quote=True)
    if form < 0.75: return mk(rng.choice([["my", "clip", "says"], ["it", "says"], ["spell", "out"]]), quote=rng.random() < 0.4)
    if form < 0.85: return mk([], quote=rng.random() < 0.5, after=rng.choice([["in", "big", "letters"], ["on", "my", "clip"], ["on", "the", "screen"]]))
    return mk(rng.choice([["with", "the", "text"], ["with", "the", "words"], ["reading"]]), quote=rng.random() < 0.6)

def contrast(fg, bg, rng):
    if (fg in DARK) == (bg in DARK) or fg == bg:
        return rng.choice(["FFFFFF", "FFE14D", "FF9CC8", "7DFFC8"]) if bg in DARK else rng.choice(["000000", "1A0033", "2F3A9E"])
    return fg

def cword(rng, hexv): return rng.choice(COLORS[hexv])

def make_example(rng):
    scene = dict(DEFAULT)
    k = rng.choice([0.35, 0.6, 1.0])   # short, medium or long sentences
    phrases = []            # list of (words, tags)
    said = set()
    # 1) vibe (sets defaults that explicit words can override)
    if rng.random() < 0.35 * k:
        names, look = rng.choice(VIBES)
        scene.update(look)
        phrases.append((rng.choice(VIBE_FORMS).format(v=rng.choice(names)).split(), None))
    # 2) text
    t = random_text(rng) if rng.random() < 0.85 else ""
    tp = text_phrase(rng, t) if t else None
    # 3) effect, speed, style
    if rng.random() < 0.7 * k:
        fx = rng.choice(FIELDS["fx"]); scene["fx"] = fx; said.add("fx")
        phrases.append((rng.choice(FX_WORDS[fx]).split(), None))
    if rng.random() < 0.45 * k:
        sp = rng.choice(["1", "3", "3", "1", "2"]); scene["sp"] = sp; said.add("sp")
        phrases.append((rng.choice(SP_WORDS[sp]).split(), None))
    if rng.random() < 0.35 * k:
        st = rng.choice(FIELDS["st"]); scene["st"] = st; said.add("st")
        phrases.append((rng.choice(ST_WORDS[st]).split(), None))
    # 4) colors
    if rng.random() < 0.55 * k:
        fg = rng.choice(FIELDS["fg"]); scene["fg"] = fg; said.add("fg")
        phrases.append((rng.choice(["{c} letters", "{c} text", "in {c}", "{c} words", "make the letters {c}", "{c} font"]).format(c=cword(rng, fg)).split(), None))
    if rng.random() < 0.25 * k:
        ac = rng.choice(FIELDS["ac"]); scene["ac"] = ac; said.add("ac")
        phrases.append((rng.choice(["{c} shadow", "{c} outline", "with a {c} outline", "{c} bubble", "{c} glow"]).format(c=cword(rng, ac)).split(), None))
    # 5) background
    bp = None
    if rng.random() < 0.55 * k:
        bp = rng.choice(FIELDS["bp"]); scene["bp"] = bp; said.add("bp")
    if rng.random() < 0.5 * k:
        bg = rng.choice(FIELDS["bg"]); scene["bg"] = bg; said.add("bg")
        if bp in ("gradient",) and rng.random() < 0.6:
            b2 = rng.choice(FIELDS["b2"]); scene["b2"] = b2; said.add("b2")
            phrases.append((rng.choice(["{a} to {b} gradient", "{a} and {b} ombre", "fade from {a} to {b}"]).format(a=cword(rng, bg), b=cword(rng, b2)).split(), None))
        elif bp and bp not in ("solid", "rainbow", "gradient") and rng.random() < 0.5:
            b2 = rng.choice(FIELDS["b2"]); scene["b2"] = b2; said.add("b2")
            pw = rng.choice(BP_WORDS[bp]).replace(" background", "")
            phrases.append((rng.choice(["{p} in {c2} on {c}", "{c2} {p} on a {c} background", "{c} background with {c2} {p}"]).format(p=pw, c=cword(rng, bg), c2=cword(rng, b2)).split(), None))
        elif bp == "gradient" and rng.random() < 0.5:
            phrases.append((f"{cword(rng, bg)} {rng.choice(['gradient', 'ombre', 'fade', 'gradient background'])}".split(), None))
        else:
            phrases.append((rng.choice(["on a {c} background", "{c} background", "on {c}", "{c} bg", "with a {c} background"]).format(c=cword(rng, bg)).split(), None))
            if bp: phrases.append((rng.choice(BP_WORDS[bp]).split(), None))
    elif bp:
        if bp not in ("solid", "rainbow", "gradient") and rng.random() < 0.35:
            b2 = rng.choice(FIELDS["b2"]); scene["b2"] = b2; said.add("b2")
            pw = rng.choice(BP_WORDS[bp]).replace(" background", "")
            phrases.append((f"{cword(rng, b2)} {pw}".split(), None))
        else:
            phrases.append((rng.choice(BP_WORDS[bp]).split(), None))
    # 6) mini me
    if rng.random() < 0.4 * k:
        av = rng.choice(FIELDS["av"][1:]); scene["av"] = av
        words = rng.choice(AV_WORDS[av]).split()
        pre = rng.choice(AV_PREFIX)
        if pre: words = [pre] + words
        if rng.random() < 0.5:
            hr = rng.choice(FIELDS["hr"]); scene["hr"] = hr
            words += ["with"] + rng.choice(HR_WORDS[hr]).split()
        phrases.append((words, None))
    # make sure the words stay readable
    if "fg" not in said: scene["fg"] = contrast(scene["fg"], scene["bg"], rng)
    # put it together in a random order (text often first, like "ROZ invert colors fast")
    rng.shuffle(phrases)
    if tp:
        pos = 0 if rng.random() < 0.45 else rng.randint(0, len(phrases))
        phrases.insert(pos, tp)
    if not phrases:
        return None
    words, tags = [], []
    for i, (w, tg) in enumerate(phrases):
        if i and rng.random() < 0.25:
            j = rng.choice([",", "and", "with", "+"])
            if j != w[0]: words.append(j); tags.append(0)
        words += w; tags += tg if tg else [0] * len(w)
    if rng.random() < 0.15: words = rng.choice([["make"], ["show"], ["i", "want"], ["can", "you", "do"], ["pls"]]) + words; tags = [0] * (len(words) - len(tags)) + tags
    if rng.random() < 0.1: words += [rng.choice(["pls", "please", "!!", "lol", "thx"])]; tags += [0]
    # glue commas onto the word before them (people type "ROZ, fast")
    out_w, out_t = [], []
    for w, tg in zip(words, tags):
        if w == "," and out_w: out_w[-1] += ","; continue
        out_w.append(w); out_t.append(tg)
    scene["t"] = t
    return dict(words=out_w, tags=out_t, scene=scene)

def make_dataset(n, seed=0):
    rng = random.Random(seed); out = []
    while len(out) < n:
        ex = make_example(rng)
        if ex and len(ex["words"]) <= 40: out.append(ex)
    return out

def scene_line(s):
    return ";".join(f"{k}={s[k]}" for k in FIELD_ORDER) + f";t={s['t']}"

def clean_word(w):
    """A word as it should appear on the clip: no quotes, no trailing comma."""
    return w.strip("\"“”‘’").rstrip(",").strip("'") or w

if __name__ == "__main__":
    for ex in make_dataset(12, seed=1):
        print(" ".join(ex["words"]))
        print("   text:", " ".join(w for w, t in zip(ex["words"], ex["tags"]) if t), "|", scene_line(ex["scene"]))
