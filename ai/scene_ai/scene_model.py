"""
Alexia's scene AI.

  sentence --(MiniLM, frozen, the same 23 MB model the app already downloads)--> one vector per word
           --(this small model, trained by us)--> the scene: effect, speed, letters, background,
                                                   colors, mini-me, hair + which words to show

The small model: a 2-layer transformer over the words, then
  - a "show this word?" yes/no for every word (picks the text out of the sentence)
  - one attention head per setting (each setting learns which words to listen to)
It is written by hand (no nn.Transformer) so the app can run the exact same math in plain JavaScript.
"""
import math, json, struct
import numpy as np
import torch, torch.nn as nn, torch.nn.functional as F
from scene_data import FIELDS, FIELD_ORDER

D_IN, D, HEADS, FF, LAYERS, MAX_WORDS = 384, 128, 4, 256, 2, 48

class Layer(nn.Module):
    def __init__(self):
        super().__init__()
        self.ln1 = nn.LayerNorm(D); self.qkv = nn.Linear(D, 3 * D); self.out = nn.Linear(D, D)
        self.ln2 = nn.LayerNorm(D); self.ff1 = nn.Linear(D, FF); self.ff2 = nn.Linear(FF, D)
    def forward(self, x, mask):            # x [B,W,D], mask [B,W] (1 = real word)
        B, W, _ = x.shape; h = D // HEADS
        q, k, v = self.qkv(self.ln1(x)).view(B, W, 3, HEADS, h).permute(2, 0, 3, 1, 4)
        att = (q @ k.transpose(-1, -2)) / math.sqrt(h)
        att = att.masked_fill(mask[:, None, None, :] == 0, -1e4).softmax(-1)
        x = x + self.out((att @ v).transpose(1, 2).reshape(B, W, D))
        return x + self.ff2(F.gelu(self.ff1(self.ln2(x)), approximate="tanh"))

class SceneAI(nn.Module):
    def __init__(self):
        super().__init__()
        self.inp = nn.Linear(D_IN, D); self.pos = nn.Parameter(torch.zeros(MAX_WORDS, D))
        self.layers = nn.ModuleList(Layer() for _ in range(LAYERS)); self.ln = nn.LayerNorm(D)
        self.tag = nn.Linear(D, 1)
        self.query = nn.Parameter(torch.randn(len(FIELD_ORDER), D) * 0.02)
        self.heads = nn.ModuleList(nn.Linear(D, len(FIELDS[f])) for f in FIELD_ORDER)
        self.drop = nn.Dropout(0.1)
    def forward(self, words, mask):        # words [B,W,384] -> (tag logits [B,W], [logits per setting])
        W = words.shape[1]
        x = self.drop(self.inp(words) + self.pos[:W])
        for L in self.layers: x = L(x, mask)
        x = self.ln(x)
        tag = self.tag(x).squeeze(-1)
        att = (x @ self.query.T) / math.sqrt(D)                       # [B,W,fields]
        att = att.masked_fill(mask[:, :, None] == 0, -1e4).softmax(1)
        pooled = att.transpose(1, 2) @ x                              # [B,fields,D]
        return tag, [h(self.drop(pooled[:, i])) for i, h in enumerate(self.heads)]

# ---------- MiniLM word vectors (same steps as the app) ----------
class WordVectors:
    """Runs MiniLM (ONNX, int8) and keeps the vector of each word's first piece."""
    def __init__(self, onnx_path, tokenizer_path):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        self.tok = Tokenizer.from_file(tokenizer_path)
        self.tok.no_padding(); self.tok.no_truncation()   # one word at a time, exactly like the app
        self.cache = {}
    def pieces(self, w):
        if w not in self.cache:
            ids = self.tok.encode(w, add_special_tokens=False).ids
            self.cache[w] = ids or [100]                 # [UNK]
        return self.cache[w]
    def __call__(self, sentences, batch=64):
        """sentences: list of word lists -> list of float32 arrays [n_words, 384]"""
        out = []
        for b in range(0, len(sentences), batch):
            chunk = sentences[b:b + batch]; rows, firsts = [], []
            for words in chunk:
                ids, first = [101], []
                for w in words[:MAX_WORDS]:
                    p = self.pieces(w)
                    if len(ids) + len(p) > 126: p = p[:max(1, 126 - len(ids))]
                    first.append(len(ids)); ids += p
                ids.append(102); rows.append(ids); firsts.append(first)
            T = max(map(len, rows))
            ids = np.zeros((len(rows), T), np.int64); am = np.zeros_like(ids)
            for i, r in enumerate(rows): ids[i, :len(r)] = r; am[i, :len(r)] = 1
            feeds = {"input_ids": ids, "attention_mask": am}
            if "token_type_ids" in [i.name for i in self.sess.get_inputs()]: feeds["token_type_ids"] = np.zeros_like(ids)
            hid = self.sess.run(None, feeds)[0]
            for i, f in enumerate(firsts): out.append(hid[i, f].astype(np.float32))
        return out

# ---------- saving for the app: int8 weights + a small JSON header in one file ----------
def export(model, path, info=None):
    """scene-ai.bin = 'SCAI' | header length (uint32) | JSON header | int8 weights.
    Each weight matrix is stored as int8 with one scale per row (value = int8 * scale)."""
    model.eval(); tensors, blobs, off = [], [], 0
    for name, t in model.state_dict().items():
        a = t.detach().float().cpu().numpy()
        a2 = a.reshape(a.shape[0], -1) if a.ndim > 1 else a.reshape(1, -1)
        scale = np.abs(a2).max(1) / 127.0; scale[scale == 0] = 1e-8
        q = np.clip(np.round(a2 / scale[:, None]), -127, 127).astype(np.int8)
        sc = scale.astype(np.float32).tobytes(); qb = q.tobytes()
        tensors.append(dict(name=name, shape=list(a.shape), rows=int(a2.shape[0]), scale_at=off, data_at=off + len(sc)))
        blob = sc + qb; blob += b"\0" * (-len(blob) % 4); blobs.append(blob); off += len(blob)
    head = dict(version=1, d_in=D_IN, d=D, heads=HEADS, ff=FF, layers=LAYERS, max_words=MAX_WORDS,
                fields=FIELD_ORDER, choices={f: FIELDS[f] for f in FIELD_ORDER}, tensors=tensors, info=info or {})
    hb = json.dumps(head).encode(); hb += b" " * (-(len(hb) + 8) % 4)
    with open(path, "wb") as f:
        f.write(b"SCAI"); f.write(struct.pack("<I", len(hb))); f.write(hb); f.write(b"".join(blobs))
    return 8 + len(hb) + off

def load_int8(model, path):
    """Loads scene-ai.bin back into a model (to check the int8 version still works)."""
    raw = open(path, "rb").read(); n = struct.unpack("<I", raw[4:8])[0]; head = json.loads(raw[8:8 + n]); base = 8 + n
    sd = {}
    for t in head["tensors"]:
        rows = t["rows"]; size = int(np.prod(t["shape"])); cols = size // rows
        sc = np.frombuffer(raw, np.float32, rows, base + t["scale_at"])
        q = np.frombuffer(raw, np.int8, size, base + t["data_at"]).reshape(rows, cols).astype(np.float32)
        sd[t["name"]] = torch.tensor((q * sc[:, None]).reshape(t["shape"]))
    model.load_state_dict(sd); return model
