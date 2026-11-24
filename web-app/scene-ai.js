// Alexia's own trained AI: a sentence in, a whole clip scene out.
//
//   "ROZ invert colors fast"  ->  fx=invert;sp=3;...;t=ROZ
//
// Step 1: MiniLM (the 23 MB language model the app already uses) turns every word
//         into 384 "meaning numbers" that depend on the words around it.
// Step 2: her small model (scene-ai.bin, trained on Kaggle, about 0.4 MB of int8 weights)
//         reads those numbers and picks every setting, plus which words to show.
// Step 2 is plain JavaScript below: the same math as ai/scene_ai/scene_model.py.
// Everything runs on the phone. After the first download it works with no signal.

import { cleanScene } from "./scene.js";

const LIB = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.3.2/dist/transformers.min.js";
const MODEL = "Xenova/all-MiniLM-L6-v2";
const WEIGHTS = "scene-ai.bin";

let mini = null;   // { tokenizer, model, Tensor }
let net = null;    // her trained model

// ---------- loading ----------
export async function hasSceneAI() {
  try { const r = await fetch(WEIGHTS, { method: "HEAD", cache: "no-store" }); return r.ok; }
  catch (e) { return !!net; }
}

export async function loadSceneAI(onProgress = () => {}) {
  if (!net) net = parseWeights(await (await fetch(WEIGHTS)).arrayBuffer());
  if (!mini) {
    const lib = await import(LIB);
    const files = {};
    // "wasm" = the safe mode that worked on Alexia's iPhone without reloading.
    const pipe = await lib.pipeline("feature-extraction", MODEL, {
      device: "wasm", dtype: "q8",
      progress_callback: (p) => {
        if (p.status === "progress" && p.total) {
          files[p.file] = [p.loaded, p.total];
          let got = 0, all = 0;
          for (const [a, b] of Object.values(files)) { got += a; all += b; }
          onProgress(got / all);
        }
      },
    });
    mini = { tokenizer: pipe.tokenizer, model: pipe.model, Tensor: lib.Tensor };
  }
  return net.info;
}

// scene-ai.bin = "SCAI" | header length | JSON header | int8 weights (one scale per row)
export function parseWeights(buf) {
  const dv = new DataView(buf);
  if (String.fromCharCode(...new Uint8Array(buf, 0, 4)) !== "SCAI") throw new Error("Not a scene-ai.bin file");
  const n = dv.getUint32(4, true);
  const head = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 8, n)));
  const base = 8 + n, W = {};
  for (const t of head.tensors) {
    const size = t.shape.reduce((a, b) => a * b, 1), cols = size / t.rows;
    const sc = new Float32Array(buf.slice(base + t.scale_at, base + t.scale_at + t.rows * 4));
    const q = new Int8Array(buf, base + t.data_at, size);
    const f = new Float32Array(size);
    for (let r = 0; r < t.rows; r++) for (let c = 0; c < cols; c++) f[r * cols + c] = q[r * cols + c] * sc[r];
    W[t.name] = f;
  }
  return { ...head, W };
}

// ---------- step 1: MiniLM word vectors ----------
async function wordVectors(words) {
  const { tokenizer, model, Tensor } = mini;
  const ids = [101], first = [];
  for (const w of words) {
    let p = tokenizer.encode(w, { add_special_tokens: false });
    if (!p.length) p = [100];
    if (ids.length + p.length > 126) p = p.slice(0, Math.max(1, 126 - ids.length));
    first.push(ids.length); ids.push(...p);
  }
  ids.push(102);
  const T = ids.length;
  const big = (a) => new Tensor("int64", BigInt64Array.from(a.map((v) => BigInt(v))), [1, T]);
  const out = await model({ input_ids: big(ids), attention_mask: big(ids.map(() => 1)), token_type_ids: big(ids.map(() => 0)) });
  const h = out.last_hidden_state.data, D = 384;
  return first.map((i) => h.slice(i * D, (i + 1) * D));
}

// ---------- step 2: her model (same math as scene_model.py) ----------
function linear(x, W, b, inD, outD) {          // x: array of rows
  return x.map((row) => {
    const y = new Float32Array(outD);
    for (let o = 0; o < outD; o++) {
      let s = b ? b[o] : 0; const off = o * inD;
      for (let i = 0; i < inD; i++) s += row[i] * W[off + i];
      y[o] = s;
    }
    return y;
  });
}
function layerNorm(x, g, b) {
  return x.map((row) => {
    const n = row.length; let m = 0, v = 0;
    for (const a of row) m += a; m /= n;
    for (const a of row) v += (a - m) * (a - m); v /= n;
    const k = 1 / Math.sqrt(v + 1e-5), y = new Float32Array(n);
    for (let i = 0; i < n; i++) y[i] = (row[i] - m) * k * g[i] + b[i];
    return y;
  });
}
const gelu = (a) => 0.5 * a * (1 + Math.tanh(0.7978845608028654 * (a + 0.044715 * a * a * a)));
function softmax(a) { const m = Math.max(...a); const e = a.map((v) => Math.exp(v - m)); const s = e.reduce((p, q) => p + q, 0); return e.map((v) => v / s); }
const add = (a, b) => a.map((row, i) => row.map((v, j) => v + b[i][j]));

function runNet(vecs) {
  const { W, d: D, heads: H, ff: FF, layers: L } = net, hd = D / H, n = vecs.length;
  let x = linear(vecs, W["inp.weight"], W["inp.bias"], net.d_in, D).map((r, i) => r.map((v, j) => v + W.pos[i * D + j]));
  for (let l = 0; l < L; l++) {
    const p = `layers.${l}.`;
    const qkv = linear(layerNorm(x, W[p + "ln1.weight"], W[p + "ln1.bias"]), W[p + "qkv.weight"], W[p + "qkv.bias"], D, 3 * D);
    const att = Array.from({ length: n }, () => new Float32Array(D));
    for (let h = 0; h < H; h++) {
      for (let i = 0; i < n; i++) {
        const sc = [];
        for (let j = 0; j < n; j++) {
          let s = 0;
          for (let k = 0; k < hd; k++) s += qkv[i][h * hd + k] * qkv[j][D + h * hd + k];
          sc.push(s / Math.sqrt(hd));
        }
        const a = softmax(sc);
        for (let j = 0; j < n; j++) for (let k = 0; k < hd; k++) att[i][h * hd + k] += a[j] * qkv[j][2 * D + h * hd + k];
      }
    }
    x = add(x, linear(att, W[p + "out.weight"], W[p + "out.bias"], D, D));
    const f1 = linear(layerNorm(x, W[p + "ln2.weight"], W[p + "ln2.bias"]), W[p + "ff1.weight"], W[p + "ff1.bias"], D, FF).map((r) => r.map(gelu));
    x = add(x, linear(f1, W[p + "ff2.weight"], W[p + "ff2.bias"], FF, D));
  }
  x = layerNorm(x, W["ln.weight"], W["ln.bias"]);
  const tag = linear(x, W["tag.weight"], W["tag.bias"], D, 1).map((r) => r[0]);
  const fields = {};
  net.fields.forEach((f, fi) => {
    const q = W.query.subarray(fi * D, (fi + 1) * D);
    const a = softmax(x.map((r) => r.reduce((s, v, j) => s + v * q[j], 0) / Math.sqrt(D)));
    const pooled = new Float32Array(D);
    x.forEach((r, i) => r.forEach((v, j) => { pooled[j] += a[i] * v; }));
    const choices = net.choices[f];
    const logits = linear([pooled], W[`heads.${fi}.weight`], W[`heads.${fi}.bias`], D, choices.length)[0];
    const pr = softmax(Array.from(logits));
    const best = pr.indexOf(Math.max(...pr));
    fields[f] = { value: choices[best], sure: pr[best], listened: a };
  });
  return { tag, fields };
}

// ---------- the main thing ----------
const cleanWord = (w) => w.replace(/^["“”‘’]+|["“”‘’]+$/g, "").replace(/,$/, "").replace(/^'+|'+$/g, "") || w;

// Returns { scene, words, shown, fields } — fields say how sure the AI was about each setting.
export async function makeScene(prompt) {
  if (!net || !mini) throw new Error("Call loadSceneAI() first");
  const words = prompt.trim().split(/\s+/).filter(Boolean).slice(0, net.max_words);
  if (!words.length) return null;
  const out = runNet(await wordVectors(words));
  const shown = out.tag.map((v) => v > 0);
  const raw = Object.fromEntries(Object.entries(out.fields).map(([f, r]) => [f, r.value]));
  raw.t = words.filter((w, i) => shown[i]).map(cleanWord).join(" ");
  return { scene: cleanScene(raw), words, shown, fields: out.fields };
}

// For tests: run step 2 on word vectors made elsewhere.
export function _runNet(vecs, weights) { net = weights; return runNet(vecs); }
