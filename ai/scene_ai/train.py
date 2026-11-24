"""
Trains Alexia's scene AI. The Kaggle notebook runs these same steps; this file is for running on a laptop.
  python train.py --minilm <folder with onnx/model_quantized.onnx and tokenizer.json> [--n 40000] [--epochs 12]
"""
import argparse, json, os, random, time
import numpy as np, torch, torch.nn.functional as F
from scene_data import make_dataset, FIELDS, FIELD_ORDER, clean_word, scene_line
from scene_model import SceneAI, WordVectors, export, load_int8, MAX_WORDS

HERE = os.path.dirname(os.path.abspath(__file__))

def encode(examples, wv):
    vecs = wv([e["words"] for e in examples])
    ys = [[FIELDS[f].index(e["scene"][f]) for f in FIELD_ORDER] for e in examples]
    tags = [e["tags"][:MAX_WORDS] for e in examples]
    avon = [e["scene"]["av"] != "none" for e in examples]
    return vecs, ys, tags, avon

def batches(data, bs, shuffle):
    vecs, ys, tags, avon = data; idx = list(range(len(vecs)))
    if shuffle: random.shuffle(idx)
    for b in range(0, len(idx), bs):
        ii = idx[b:b + bs]; W = max(len(vecs[i]) for i in ii)
        x = np.zeros((len(ii), W, 384), np.float32); m = np.zeros((len(ii), W), np.float32); t = np.zeros((len(ii), W), np.float32)
        for j, i in enumerate(ii):
            n = len(vecs[i]); x[j, :n] = vecs[i]; m[j, :n] = 1; t[j, :n] = tags[i]
        yield (torch.tensor(x), torch.tensor(m), torch.tensor(t),
               torch.tensor([ys[i] for i in ii]), torch.tensor([avon[i] for i in ii], dtype=torch.float32))

HR = FIELD_ORDER.index("hr")
def loss_fn(model, x, m, t, y, avon):
    tag, outs = model(x, m)
    loss = (F.binary_cross_entropy_with_logits(tag, t, reduction="none") * m).sum() / m.sum()
    for i, o in enumerate(outs):
        l = F.cross_entropy(o, y[:, i], reduction="none")
        if i == HR: l = l * avon            # hair only matters when mini-me is on
        loss = loss + l.mean()
    return loss, tag, outs

def evaluate(model, data):
    model.eval(); right = np.zeros(len(FIELD_ORDER)); n = 0; text_ok = 0
    with torch.no_grad():
        for x, m, t, y, avon in batches(data, 256, False):
            tag, outs = model(x, m)
            for i, o in enumerate(outs): right[i] += (o.argmax(1) == y[:, i]).sum().item()
            text_ok += (((tag > 0).float() == t) | (m == 0)).all(1).sum().item(); n += len(y)
    model.train()
    return {f: right[i] / n for i, f in enumerate(FIELD_ORDER)} | {"text": text_ok / n}

def train(train_data, val_data, epochs=12, lr=2e-3, log=print):
    torch.manual_seed(0); random.seed(0)
    model = SceneAI(); opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    steps = epochs * ((len(train_data[0]) + 127) // 128)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps)
    for ep in range(epochs):
        t0 = time.time(); tot = 0; k = 0
        for x, m, t, y, avon in batches(train_data, 128, True):
            # a little noise, so it copes with the phone's slightly different numbers
            x = x + torch.randn_like(x) * 0.02
            loss, _, _ = loss_fn(model, x, m, t, y, avon)
            opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step()
            tot += loss.item(); k += 1
        acc = evaluate(model, val_data)
        log(f"round {ep + 1}/{epochs}  loss {tot / k:.3f}  text {acc['text']:.1%}  effect {acc['fx']:.1%}  "
            f"background {acc['bp']:.1%}  mini-me {acc['av']:.1%}  letters color {acc['fg']:.1%}  ({time.time() - t0:.0f}s)")
    return model

def predict(model, wv, sentence):
    words = sentence.split()[:MAX_WORDS]
    if not words: return None
    x = torch.tensor(wv([words])[0])[None]; m = torch.ones(1, len(words))
    model.eval()
    with torch.no_grad(): tag, outs = model(x, m)
    scene = {f: FIELDS[f][o[0].argmax().item()] for f, o in zip(FIELD_ORDER, outs)}
    scene["t"] = " ".join(clean_word(w) for w, k in zip(words, tag[0]) if k > 0)[:24]
    return scene

def check_tests(model, wv, tests, log=print):
    """tests: [{prompt, expect: {field: value}}] written by hand, phrased differently from the practice examples."""
    ok = tot = 0; whole = 0
    for tcase in tests:
        got = predict(model, wv, tcase["prompt"]); bad = []
        for f, v in tcase["expect"].items():
            tot += 1
            if str(got[f]).lower() == str(v).lower(): ok += 1
            else: bad.append(f"{f}: wanted {v}, got {got[f]}")
        whole += not bad
        log(("✅ " if not bad else "❌ ") + tcase["prompt"] + ("" if not bad else "   (" + "; ".join(bad) + ")"))
    log(f"\nHand-written tests: {whole}/{len(tests)} sentences fully right, {ok}/{tot} settings right ({ok / tot:.0%})")
    return ok / tot

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--minilm", required=True); ap.add_argument("--n", type=int, default=40000)
    ap.add_argument("--epochs", type=int, default=12); ap.add_argument("--out", default="scene-ai.bin")
    a = ap.parse_args()
    wv = WordVectors(os.path.join(a.minilm, "onnx", "model_quantized.onnx"), os.path.join(a.minilm, "tokenizer.json"))
    t0 = time.time()
    tr = encode(make_dataset(a.n, seed=1), wv); va = encode(make_dataset(2000, seed=2), wv)
    print(f"word vectors ready in {time.time() - t0:.0f}s")
    model = train(tr, va, a.epochs)
    tests = json.load(open(os.path.join(HERE, "test_prompts.json")))
    check_tests(model, wv, tests)
    size = export(model, a.out, info=dict(examples=a.n, epochs=a.epochs))
    print(f"saved {a.out} ({size / 1024:.0f} KB)")
    m2 = load_int8(SceneAI(), a.out); print("int8 version:"); check_tests(m2, wv, tests, log=lambda s: None if s[:1] in "✅❌" else print(s))

def example_from_line(prompt, line):
    """Turns one of YOUR examples ("ROZ invert colors fast", "fx=invert;sp=3;t=ROZ") into practice data.
    Settings you leave out get the normal defaults. The words in t= are marked as the words to show."""
    from scene_data import DEFAULT
    scene = dict(DEFAULT); scene["t"] = ""
    ti = line.find("t=")
    if ti >= 0 and (ti == 0 or line[ti - 1] == ";"): scene["t"] = line[ti + 2:]; line = line[:ti]
    for part in line.split(";"):
        if "=" in part:
            k, v = part.split("=", 1); k = k.strip(); v = v.strip()
            if k in FIELDS:
                v = v.upper() if k in ("fg", "ac", "bg", "b2") else v
                if v not in FIELDS[k]: raise ValueError(f"{k}={v} isn't one of {FIELDS[k]}")
                scene[k] = v
    words = prompt.split(); want = [w.lower() for w in scene["t"].split()]; tags = [0] * len(words)
    for i in range(len(words)):
        if want and [clean_word(w).lower() for w in words[i:i + len(want)]] == want:
            tags[i:i + len(want)] = [1] * len(want); break
    else:
        if want: raise ValueError(f'Couldn\'t find the words "{scene["t"]}" in "{prompt}"')
    return dict(words=words, tags=tags, scene=scene)
