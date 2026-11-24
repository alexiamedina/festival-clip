"""Builds train-scene-ai.ipynb (the Kaggle notebook) from the .py files in this folder, so they never drift apart."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
src = lambda f: open(os.path.join(HERE, f)).read()

cells = []
def md(t): cells.append(dict(cell_type="markdown", metadata={}, source=t.strip()))
def code(t): cells.append(dict(cell_type="code", metadata={}, execution_count=None, outputs=[], source=t.strip()))

md("""
# ✨ Train Alexia's Rave Clip AI

This notebook teaches a small AI to turn a sentence like **"ROZ invert colors fast"** into a scene for the clip:
which words to show, the effect, the speed, letter style, colors, background, and mini me.

**How it works**
1. **Practice examples.** A generator writes about 40,000 sentences, each with the right scene for it. You can add your own too.
2. **Meaning numbers.** MiniLM, a small language model the app already uses, turns every word into 384 numbers.
   It stays *frozen*, which means we don't change it.
3. **Training.** A small transformer (about 300k numbers to learn) learns to pick every setting, plus which words to put on the clip.
4. **Export.** The trained weights are squeezed to int8, about 0.4 MB, and saved as `scene-ai.bin`.
   The app runs it right on the phone with no internet.

**To run:** turn on the internet (top menu **Settings → Turn on internet**, or right-hand panel **Session options → Internet**), then click **Run All**. The first cell tells you clearly if the internet is still off.
It takes about 10 minutes on Kaggle's free CPU. No GPU is needed.
""")
code("""
# 1. Check the internet, get the tools + MiniLM (the same 23 MB int8 model the app downloads)
import os, sys, subprocess, urllib.request, socket
try:
    socket.create_connection(("huggingface.co", 443), timeout=5).close()
except OSError:
    raise SystemExit(
        "\\n🚫 This notebook can't reach the internet yet.\\n"
        "Turn it on: top menu  Settings  ->  Turn on internet\\n"
        "   (or the right-hand panel: Session options -> Internet -> On.\\n"
        "    If the panel is hidden, click the little arrow at the far right edge.)\\n"
        "If there's no Internet switch at all, verify your phone number first:\\n"
        "   kaggle.com -> your picture -> Settings -> Phone verification.\\n"
        "Then click Run All again.")
need = []
for mod, pkg in [("onnxruntime", "onnxruntime"), ("tokenizers", "tokenizers")]:
    try: __import__(mod)
    except ImportError: need.append(pkg)
if need:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q"] + need)
os.makedirs("minilm/onnx", exist_ok=True)
BASE = "https://huggingface.co/Xenova/all-MiniLM-L6-v2/resolve/main/"
for f in ["onnx/model_quantized.onnx", "tokenizer.json"]:
    if not os.path.exists("minilm/" + f):
        urllib.request.urlretrieve(BASE + f, "minilm/" + f)
print("✅ Internet OK. MiniLM ready:", os.path.getsize("minilm/onnx/model_quantized.onnx") // 1_000_000, "MB")
""")
md("## 2. The code\nThese cells save the project's Python files next to the notebook (the same files as `ai/scene_ai/` on your computer).")
for f in ["scene_data.py", "scene_model.py", "train.py"]:
    code(f"%%writefile {f}\n" + src(f))
code("%%writefile test_prompts.json\n" + src("test_prompts.json"))
md("""
## 3. Your own examples (optional, but this is what makes it *yours*)
Add sentences the way YOU would type them, with the scene you want. Each one counts 30 times in training.
Leave out any setting you don't care about. Use the words exactly as they appear in the app:
- `fx` effect: still, scroll, wave, bounce, invert, rainbow, glitch, type, pulse
- `sp` speed: 1 slow, 2 medium, 3 fast
- `st` letters: plain, shadow, outline
- `bp` background: solid, gradient, checker, stripes, dots, stars, hearts, sparkles, rainbow
- `av` mini me: none, smile, teeth, ooh, grin, chill, dance1, dance2, dance3, and `hr` hair: straight, curly
- colors `fg` letters, `ac` shadow/outline, `bg` background, `b2` pattern: FFFFFF 000000 1A0033 3B2B2E F7EEDD FF9CC8 FF2FA0 FF4A55 FF9A3C FFE14D 8FE36B 7DFFC8 5AA8FF 2F3A9E A06BFF C9B5FF
- `t` the words to show. They must appear in your sentence.
""")
code("# Your examples (about 90 to start, written like you talk). Add more at the bottom!\n" + src("my_examples.py"))
md("## 4. Make the practice examples")
code('''
import random, json, time
from scene_data import make_dataset, scene_line
from train import example_from_line
train_ex = make_dataset(40000, seed=1)
val_ex = make_dataset(2000, seed=2)
mine = [example_from_line(p, l) for p, l in MY_EXAMPLES]
train_ex += mine * 30
random.Random(0).shuffle(train_ex)
print(len(train_ex), "practice examples. A few of them:\\n")
for e in train_ex[:8]:
    print(" ".join(e["words"]))
    print("    ->", scene_line(e["scene"]), "\\n")
''')
md("## 5. Turn every sentence into meaning numbers with MiniLM\nThis is the slow part, a few minutes.")
code('''
from scene_model import WordVectors
from train import encode
wv = WordVectors("minilm/onnx/model_quantized.onnx", "minilm/tokenizer.json")
t0 = time.time()
train_data = encode(train_ex, wv)
val_data = encode(val_ex, wv)
print(f"done in {time.time() - t0:.0f} s")
''')
md("## 6. Train!\nEach round goes through all the examples once. Watch the scores go up.")
code('''
from train import train
model = train(train_data, val_data, epochs=12)
''')
md("## 7. The real test: sentences it has never seen\nThese were written by hand, phrased differently from the practice examples.")
code('''
from train import check_tests, predict
tests = json.load(open("test_prompts.json"))
score = check_tests(model, wv, tests)
''')
md("### Try your own sentences")
code('''
for s in ["ROZ invert colors fast", "PLUR in pink bubble letters with hearts", "me doing dance 2 with straight hair saying HI"]:
    print(s, "\\n   ->", predict(model, wv, s))
''')
md("## 8. Save it for the app\nThis saves `scene-ai.bin`. Click the link to download it, then follow the guide to put it in the app.")
code('''
from scene_model import export, load_int8, SceneAI
size = export(model, "scene-ai.bin", info=dict(examples=len(train_ex), epochs=12, my_examples=len(MY_EXAMPLES), test_score=round(score, 3)))
print(f"scene-ai.bin: {size / 1024:.0f} KB")
check = load_int8(SceneAI(), "scene-ai.bin")
print("int8 check:"); check_tests(check, wv, tests, log=lambda s: None if s[:1] in "✅❌" else print(s))
from IPython.display import FileLink
FileLink("scene-ai.bin")
''')

nb = dict(nbformat=4, nbformat_minor=5, cells=cells,
          metadata=dict(kernelspec=dict(name="python3", display_name="Python 3", language="python"),
                        language_info=dict(name="python")))
for c in nb["cells"]:
    lines = c["source"].split("\n"); c["source"] = [l + "\n" for l in lines[:-1]] + [lines[-1]]
json.dump(nb, open(os.path.join(HERE, "train-scene-ai.ipynb"), "w"), indent=1)
print("wrote train-scene-ai.ipynb with", len(cells), "cells")
