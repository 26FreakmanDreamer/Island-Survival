"""Collect the newest Seedream output for each named frame into an action folder."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-root", default="assets/generated/raw/lina_frames")
    parser.add_argument("--action", required=True)
    parser.add_argument("--names", required=True, help="comma-separated custom_name prefixes in order")
    parser.add_argument("--dest", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path.cwd()
    src_root = (root / args.src_root).resolve()
    dest = (root / args.dest).resolve()
    names = [name.strip() for name in args.names.split(",") if name.strip()]
    if not args.dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    for index, name in enumerate(names):
        candidates = sorted(
            src_root.rglob(f"{name}*.png"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            print(f"MISSING {name}")
            continue
        source = candidates[0]
        target = dest / f"{args.action}_{index:02d}.png"
        print(f"{name}: {source} -> {target}")
        if not args.dry_run:
            shutil.copy2(source, target)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
