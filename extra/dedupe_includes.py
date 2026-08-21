#!/usr/bin/env python3

# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# Finds files that are byte-identical, at the same relative path, across every
# one of a set of input directories, copies one canonical copy of each into a
# separate output directory (preserving its relative path), then deletes the
# duplicate copies from the input directories.
#
# If a directory sits under a "variants/<board>/" tree with a sibling
# "includes.txt" (a list of "-iwithprefixbefore<path>" compiler flags, each
# path relative to the variant's own directory), that file is updated to
# match: entries fully emptied by the move are repointed at the mirrored
# common directory and their now-empty source directory is deleted; entries
# only partially emptied get an extra entry added for the common directory
# alongside the original. This only happens when not running with --dry-run.

import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path

INCLUDE_FLAG = "-iwithprefixbefore"


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


def find_variant_root(path: Path) -> Path | None:
    parts = path.parts
    for i, part in enumerate(parts):
        if part == "variants" and i + 1 < len(parts):
            return Path(*parts[: i + 2])
    return None


def update_includes_txt(
    variant_root: Path, input_dir: Path, common_dir: Path, common_rel_paths
) -> None:
    includes_txt = variant_root / "includes.txt"
    if not includes_txt.is_file():
        return

    lines = includes_txt.read_text().splitlines()
    entries = [
        (i, line[len(INCLUDE_FLAG) :])
        for i, line in enumerate(lines)
        if line.startswith(INCLUDE_FLAG)
    ]
    # Deepest first, so a child directory is resolved (and possibly removed)
    # before its parent's emptiness is checked.
    entries.sort(key=lambda e: e[1].count("/"), reverse=True)

    actions: dict[int, tuple[str, str]] = {}
    for idx, suffix in entries:
        real_dir = variant_root / suffix.lstrip("/")
        if real_dir != input_dir and input_dir not in (real_dir, *real_dir.parents):
            continue

        affected = any(
            (input_dir / rel) == real_dir or real_dir in (input_dir / rel).parents
            for rel in common_rel_paths
        )
        if not affected:
            continue

        if real_dir.exists():
            has_files = any(p.is_file() for p in real_dir.rglob("*"))
        else:
            has_files = False

        sub_path = real_dir.relative_to(input_dir)
        common_target = common_dir if sub_path == Path(".") else common_dir / sub_path
        new_suffix = "/" + os.path.relpath(common_target, variant_root).replace(os.sep, "/")
        new_line = INCLUDE_FLAG + new_suffix

        if not has_files:
            if real_dir.exists():
                shutil.rmtree(real_dir)
            actions[idx] = ("replace", new_line)
        else:
            actions[idx] = ("augment", new_line)

    if not actions:
        return

    new_lines = []
    for i, line in enumerate(lines):
        action = actions.get(i)
        if action is None:
            new_lines.append(line)
        elif action[0] == "replace":
            new_lines.append(action[1])
        else:
            new_lines.append(line)
            new_lines.append(action[1])

    includes_txt.write_text("\n".join(new_lines) + "\n")


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

    for d in args.directories:
        variant_root = find_variant_root(d)
        if variant_root is not None:
            update_includes_txt(variant_root, d, args.common_dir, common.keys())

    return 0


if __name__ == "__main__":
    sys.exit(main())
