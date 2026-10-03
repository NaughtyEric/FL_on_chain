#!/usr/bin/env python
"""Download CIFAR-100 from the HuggingFace Hub into the layout fl_client expects.

``data/`` is gitignored, so a fresh clone has no dataset. This script fetches
``uoft-cs/cifar100`` (parquet, ~140 MB) and writes it as HuggingFace arrow
*stream* files with the dataset features embedded in the schema metadata:

    data/cifar100/cifar100-train.arrow   50,000 rows
    data/cifar100/cifar100-test.arrow    10,000 rows
    data/cifar100/dataset_info.json

which is exactly what ``fl_client.dataset.load_cifar100`` reads via
``load_dataset("arrow", data_dir=...)`` (the ``train``/``test`` tokens in the
file names drive split detection). Features: ``img`` (PNG bytes), ``fine_label``
(100 classes), ``coarse_label`` (20 superclasses; the label the project trains on).

Run from the repo root with the venv python (idempotent; skips splits already present):
    .venv/Scripts/python scripts/fetch_data.py [--data-dir data/cifar100] [--force]
Set ``HF_ENDPOINT`` (e.g. a mirror) if the Hub is slow to reach.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow as pa
from datasets import load_dataset

HF_DATASET = "uoft-cs/cifar100"
SPLITS = {"train": 50_000, "test": 10_000}
EXPECTED_FEATURES = ("img", "fine_label", "coarse_label")


def write_stream(table: pa.Table, path: Path) -> None:
    """Write a pyarrow table as an arrow IPC *stream* (what `datasets` reads back)."""
    tmp = path.with_suffix(".arrow.part")
    with pa.OSFile(str(tmp), "wb") as sink, pa.ipc.new_stream(sink, table.schema) as writer:
        for batch in table.to_batches(max_chunksize=1_000):
            writer.write_batch(batch)
    tmp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch CIFAR-100 into data/cifar100 (HF arrow layout).")
    parser.add_argument("--data-dir", default="data/cifar100", help="target directory (default data/cifar100)")
    parser.add_argument("--force", action="store_true", help="re-download even if the files exist")
    args = parser.parse_args()

    out = Path(args.data_dir)
    out.mkdir(parents=True, exist_ok=True)
    targets = {split: out / f"cifar100-{split}.arrow" for split in SPLITS}
    if not args.force and all(p.is_file() for p in targets.values()) and (out / "dataset_info.json").is_file():
        print(f"{out} already populated; use --force to re-download")
        return

    print(f"downloading {HF_DATASET} from the HuggingFace Hub ...")
    ds = load_dataset(HF_DATASET)
    info = None
    for split, expected in SPLITS.items():
        d = ds[split]
        missing = [f for f in EXPECTED_FEATURES if f not in d.features]
        if missing:
            raise SystemExit(f"{HF_DATASET}[{split}] lacks expected features {missing}: got {list(d.features)}")
        if len(d) != expected:
            raise SystemExit(f"{HF_DATASET}[{split}] has {len(d)} rows, expected {expected}")
        # d.data.table carries the HF features in schema metadata, so the arrow
        # file is self-describing and load_dataset("arrow") recovers Image/ClassLabel.
        write_stream(d.data.table, targets[split])
        print(f"  wrote {targets[split]}  ({len(d)} rows, {targets[split].stat().st_size / 1e6:.1f} MB)")
        info = info or d.info

    assert info is not None
    (out / "dataset_info.json").write_text(
        json.dumps(
            {
                "description": info.description or "",
                "citation": info.citation or "",
                "homepage": info.homepage or "",
                "license": info.license or "",
                "features": info.features.to_dict(),
                "dataset_name": "cifar100",
                "splits": {s: {"name": s, "num_examples": n} for s, n in SPLITS.items()},
                "source": HF_DATASET,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"done: {out}")


if __name__ == "__main__":
    main()
