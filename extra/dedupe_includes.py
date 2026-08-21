#!/usr/bin/env python3

# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# Finds files that are byte-identical, at the same relative path, across every
# one of a set of input directories, copies one canonical copy of each into a
# separate output directory (preserving its relative path), then deletes the
# duplicate copies from the input directories.
#
# This will require a separate build configuration --
# re-pointing include search paths at the output directory is a separate,
# manual step.

import argparse
import hashlib
import sys
from pathlib import Path


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_directory(directory: Path) -> dict[Path, str]:
    return {
        path.relative_to(directory): hash_file(path)
        for path in directory.rglob("*")
        if path.is_file()
    }


def find_common_files(per_dir_hashes: list[dict[Path, str]]) -> dict[Path, str]:
    common = {}
    first, rest = per_dir_hashes[0], per_dir_hashes[1:]
    for rel_path, digest in first.items():
        if all(other.get(rel_path) == digest for other in rest):
            common[rel_path] = digest
    return common


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--common-dir",
        required=True,
        type=Path,
        help="output directory to mirror common files into; must not already exist",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be done, without touching the filesystem",
    )
    parser.add_argument(
        "directories",
        nargs="+",
        type=Path,
        help="two or more directories to compare",
    )
    args = parser.parse_args()

    if len(args.directories) < 2:
        parser.error("need at least 2 directories to compare")

    if args.common_dir.exists():
        parser.error(f"--common-dir {args.common_dir} already exists")

    per_dir_hashes = [scan_directory(d) for d in args.directories]
    common = find_common_files(per_dir_hashes)

    total_size = sum(
        (args.directories[0] / rel_path).stat().st_size for rel_path in common
    )
    freed = total_size * (len(args.directories) - 1)

    print(f"{len(args.directories)} directories compared")
    for d, hashes in zip(args.directories, per_dir_hashes):
        print(f"  {d}: {len(hashes)} files")
    print(f"{len(common)} files common to all directories")
    print(f"{freed} bytes would be freed" if args.dry_run else f"{freed} bytes freed")

    if args.dry_run:
        return 0

    for rel_path in common:
        src = args.directories[0] / rel_path
        dst = args.common_dir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        if hash_file(dst) != common[rel_path]:
            print(f"error: mirrored copy of {rel_path} does not match source", file=sys.stderr)
            return 1

    for rel_path in common:
        for d in args.directories:
            (d / rel_path).unlink()

    return 0


if __name__ == "__main__":
    sys.exit(main())
