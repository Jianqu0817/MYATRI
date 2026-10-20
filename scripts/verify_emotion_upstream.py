"""Compare the inspected, pinned upstream pure math to our adaptation.

No installation or network. Run with --source PATH to the reviewed checkout.
Only affect.py / mood.py are executed, after checking their pinned Git blobs.
The full upstream engine, stores, plugins and model adapters are never loaded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import types
from datetime import datetime, timedelta, timezone

from myatri._vendor.emotional_memory import lerp_pad, pad_distance, regress_pad, update_mood


COMMIT = "8b84bf3725448f2545337c08e346434819c01628"


def git_blob(root, path):
    return subprocess.check_output(["git", "-C", str(root), "show", f"{COMMIT}:{path}"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/emotion_upstream_parity.json"))
    args = parser.parse_args()
    source = args.source.resolve()
    actual = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if actual != COMMIT:
        raise ValueError("upstream checkout is not the reviewed commit")
    # Use canonical Git bytes, never an edited checkout file.
    blobs = {name: git_blob(source, f"src/emotional_memory/{name}.py") for name in ("affect", "mood")}
    package = types.ModuleType("emotional_memory")
    package.__path__ = []
    sys.modules["emotional_memory"] = package
    for name, blob in blobs.items():
        module = types.ModuleType(f"emotional_memory.{name}")
        sys.modules[module.__name__] = module
        exec(compile(blob, f"pinned-upstream/{name}.py", "exec"), module.__dict__)
    affect, mood = sys.modules["emotional_memory.affect"], sys.modules["emotional_memory.mood"]
    rng, maximum, comparisons = random.Random(20261020), 0.0, 0
    start = datetime(2026, 10, 20, tzinfo=timezone.utc)
    for _ in range(250):
        left = (rng.uniform(-1, 1), rng.random(), rng.random())
        right = (rng.uniform(-1, 1), rng.random(), rng.random())
        alpha, inertia, half_life, elapsed = rng.random(), rng.random(), rng.uniform(1, 100000), rng.uniform(0, 500000)
        a, b = affect.CoreAffect(valence=left[0], arousal=left[1], dominance=left[2]), affect.CoreAffect(valence=right[0], arousal=right[1], dominance=right[2])
        m = mood.MoodField(valence=left[0], arousal=left[1], dominance=left[2], inertia=inertia, timestamp=start)
        cfg = mood.MoodDecayConfig(base_half_life_seconds=half_life, baseline_valence=right[0], baseline_arousal=right[1], baseline_dominance=right[2])
        expected_regress = m.regress(start + timedelta(seconds=elapsed), cfg)
        expected_update = m.update(b, alpha, now=start)
        expected_lerp = a.lerp(b, alpha)
        def vector(value):
            return value.valence, value.arousal, value.dominance
        # datetime has microsecond precision; use exactly the same elapsed.
        exact_elapsed = ((start + timedelta(seconds=elapsed)) - start).total_seconds()
        pairs = [(regress_pad(left, right, exact_elapsed, half_life, inertia), vector(expected_regress)),
                 (update_mood(left, right, alpha, inertia), vector(expected_update)),
                 (lerp_pad(left, right, alpha), vector(expected_lerp)),
                 ((pad_distance(left, right),), (a.distance(b),))]
        for actual_values, expected in pairs:
            maximum = max(maximum, *(abs(x-y) for x, y in zip(actual_values, expected, strict=True)))
            comparisons += 1
    assert maximum <= 1e-12, maximum
    output = {"repository": "gianlucamazza/emotional-memory", "commit": COMMIT,
              "cases": 250, "comparisons": comparisons, "max_absolute_error": maximum,
              "tolerance": 1e-12, "passed": True, "new_model_api_calls": 0,
              "git_blob_sha256": {name: hashlib.sha256(blob).hexdigest() for name, blob in blobs.items()}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
