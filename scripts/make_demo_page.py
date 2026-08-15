#!/usr/bin/env python
"""Generate a self-contained local HTML page visualizing CIFAR-100 predictions.

Samples ``--num`` random CIFAR-100 test images, runs the ``CIFAR100ResNet``
(with weights from a checkpoint) on them, and embeds the image + true coarse
label + predicted label + confidence into a single HTML file. Open that file in
a browser and click the button to reveal a fresh random group of samples.

Weights resolution (first match wins):
    --weights arg                     (default artifacts/pretrained_cifar100.npz)
    artifacts/global_parameters.npz   (FL run output)
    random initialization              (with a warning; predictions will look random)

Run from the repo root with the venv python:
    .venv/Scripts/python scripts/make_demo_page.py [--weights artifacts/pretrained_cifar100.npz] \
        [--num 30] [--show 6] [--data-dir data/cifar100] [--out artifacts/demo.html]
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import random
from pathlib import Path

import torch
from datasets import load_dataset as hf_load_dataset

from fl_client.dataset import CIFAR_TRANSFORM
from fl_client.device import select_device
from fl_client.model import CIFAR100ResNet, COARSE_CLASSES
from fl_client.parameters import load_parameters, set_parameters


def _image_data_url(pil_image: object) -> str:
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CIFAR-100 粗粒度预测演示</title>
<style>
  :root { color-scheme: dark; }
  body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background: #111418; color: #e6e8eb; margin: 0; padding: 24px; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  .sub { color: #8b949e; font-size: 13px; margin-bottom: 16px; }
  .stats { display: inline-block; padding: 4px 10px; border-radius: 999px; background: #1c2128; font-size: 13px; margin-bottom: 16px; }
  button { background: #2f81f7; color: white; border: none; padding: 10px 18px; border-radius: 8px; font-size: 14px; cursor: pointer; }
  button:hover { background: #2f6ed4; }
  #grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; margin-top: 20px; }
  .card { background: #1c2128; border: 1px solid #30363d; border-radius: 10px; padding: 12px; }
  .card img { width: 96px; height: 96px; image-rendering: pixelated; border-radius: 6px; display: block; margin: 0 auto 10px; background:#000; }
  .lbl { font-size: 13px; margin: 2px 0; }
  .true { color: #7ee787; }
  .false { color: #ff7b72; }
  .badge { display: inline-block; font-size: 11px; padding: 1px 8px; border-radius: 999px; }
  .badge.ok { background: #1a7f37; color: #d1f7c4; }
  .badge.no { background: #a40e26; color: #ffdcd7; }
  .conf { color: #8b949e; font-size: 12px; margin-top: 6px; }
  .empty { color: #8b949e; margin-top: 20px; }
</style>
</head>
<body>
  <h1>CIFAR-100 粗粒度分类 —— 预测演示</h1>
  <div class="sub">模型：CIFAR100ResNet · 测试集：${DATA_DIR} · 权重：${WEIGHTS}</div>
  <div class="stats">池内 ${NUM} 个样本，模型正确 <span id="poolOk">?</span> / ${NUM}</div>
  <button onclick="sample()">随机抽一组（${SHOW} 张）</button>
  <div id="grid" class="empty">点击按钮查看预测结果。</div>
<script>
const SAMPLES = __SAMPLES__;
let cursor = 0;
document.getElementById("poolOk").textContent = SAMPLES.filter(s => s.ok).length;

function sample() {
  // 每点一次从池里随机取一组（避免连取到同一批）。
  const pool = [...SAMPLES];
  const picked = [];
  for (let i = 0; i < ${SHOW} && pool.length; i++) {
    const k = Math.floor(Math.random() * pool.length);
    picked.push(pool.splice(k, 1)[0]);
  }
  const grid = document.getElementById("grid");
  grid.className = "";
  grid.innerHTML = picked.map(s => `
    <div class="card">
      <img src="${s.img}" alt="sample">
      <div class="lbl">真实：<span class="${s.ok ? "true" : "false"}">${s.true}</span></div>
      <div class="lbl">预测：<span class="${s.ok ? "true" : "false"}">${s.pred}</span></div>
      <div class="conf">置信度 ${(s.conf * 100).toFixed(1)}% <span class="badge ${s.ok ? "ok" : "no"}">${s.ok ? "OK" : "X"}</span></div>
    </div>`).join("");
}
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a local HTML page of CIFAR-100 predictions.")
    parser.add_argument("--weights", default="artifacts/pretrained_cifar100.npz",
                        help="checkpoint to load (default artifacts/pretrained_cifar100.npz)")
    parser.add_argument("--num", type=int, default=30, help="number of test samples to embed (default 30)")
    parser.add_argument("--show", type=int, default=6, help="samples revealed per button click (default 6)")
    parser.add_argument("--data-dir", default="data/cifar100",
                        help="HuggingFace CIFAR-100 arrow directory (default data/cifar100)")
    parser.add_argument("--seed", type=int, default=0, help="RNG seed for reproducible sampling (default 0)")
    parser.add_argument("--out", default="artifacts/demo.html", help="HTML output path (default artifacts/demo.html)")
    args = parser.parse_args()

    device = select_device("auto")
    model = CIFAR100ResNet(num_classes=COARSE_CLASSES).to(device)

    weights = Path(args.weights)
    if not weights.is_file():
        fallback = Path("artifacts/global_parameters.npz")
        print(f"note: {weights} not found; trying {fallback}", flush=True)
        weights = fallback
    if weights.is_file():
        set_parameters(model, load_parameters(weights))  # raises if shapes mismatch
        print(f"loaded weights from {weights}", flush=True)
    else:
        print(f"warning: no checkpoint found; using random initialization (predictions will look random)", flush=True)

    model.eval()
    hf_test = hf_load_dataset("arrow", data_dir=args.data_dir)["test"]
    coarse_names = hf_test.features["coarse_label"].names
    rng = random.Random(args.seed)
    indices = rng.sample(range(len(hf_test)), min(args.num, len(hf_test)))

    samples = []
    with torch.no_grad():
        for index in indices:
            row = hf_test[index]
            tensor = CIFAR_TRANSFORM(row["img"]).unsqueeze(0).to(device)
            probs = torch.softmax(model(tensor), dim=1)[0]
            pred = int(probs.argmax())
            true = int(row["coarse_label"])
            samples.append({
                "img": _image_data_url(row["img"]),
                "true": coarse_names[true],
                "pred": coarse_names[pred],
                "conf": float(probs[pred]),
                "ok": pred == true,
            })

    correct = sum(s["ok"] for s in samples)
    print(f"model correct on embedded pool: {correct}/{len(samples)} ({correct / len(samples):.1%})", flush=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    html = (
        TEMPLATE.replace("${DATA_DIR}", args.data_dir)
        .replace("${WEIGHTS}", str(weights))
        .replace("${NUM}", str(len(samples)))
        .replace("${SHOW}", str(args.show))
        .replace("__SAMPLES__", json.dumps(samples))
    )
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} — open it in a browser and click the button", flush=True)


if __name__ == "__main__":
    main()
