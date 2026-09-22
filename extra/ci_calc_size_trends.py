#!/usr/bin/env python3

# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# Script to extract trends and flag outliers from the delta reports produced
# by extra/ci_calc_size_reports.py.
#
# This script expects a directory of "<package>-<board>-link_mode=<mode>.json"
# report files (each already annotated with per-sketch "delta" data) and
# prints/writes a JSON summary of sketches whose delta is a statistical
# outlier vs. its own board/link_mode's distribution. Boards are not
# comparable to one another (each has its own typical delta, e.g. from
# board-specific code paths), so outliers are computed within each board's
# own group of sketches rather than pooling everything into one global
# distribution.

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

SIZE_NAMES = ("flash", "RAM for global variables")

def parse_filename(name):
    """
    Parse a report filename of the form
    "<package_prefix>-<package>-<board>-link_mode=<mode>.json" into its
    (package, board, link_mode) components, matching the naming convention
    used by ci_calc_size_reports.py.
    """

    package, board, opts = name[:-5].split('-')[1:4]
    link_mode = opts.split('=', 1)[1] if '=' in opts else opts
    return package, board, link_mode

def load_records(input_dir):
    """
    Load every report JSON file in input_dir and flatten it into one record
    per successfully-compiled sketch, keeping only sketches with valid
    (numeric) flash and RAM deltas.
    """

    records = []
    for path in sorted(Path(input_dir).glob("*.json")):
        with open(path) as f:
            data = json.load(f)
        package, board, link_mode = parse_filename(path.name)
        for sketch in data["boards"][0]["sketches"]:
            if not sketch.get("compilation_success", False):
                continue
            sizes = {entry["name"]: entry for entry in sketch["sizes"]}
            flash = sizes.get("flash")
            ram = sizes.get("RAM for global variables")
            if not flash or not ram:
                continue
            flash_delta = flash.get("delta")
            ram_delta = ram.get("delta")
            if not flash_delta or not ram_delta:
                continue
            if isinstance(flash_delta["absolute"], str) or isinstance(ram_delta["absolute"], str):
                # "N/A", previous size was zero/missing
                continue
            records.append({
                "package": package,
                "board": board,
                "link_mode": link_mode,
                "sketch": sketch["name"],
                "flash_delta_abs": flash_delta["absolute"],
                "flash_delta_rel": flash_delta["relative"],
                "ram_delta_abs": ram_delta["absolute"],
                "ram_delta_rel": ram_delta["relative"],
                "flash_max": flash["maximum"],
                "ram_max": ram["maximum"],
            })
    return records

def mad_outliers(records, key, threshold=3.5):
    """
    Flag records whose field is a robust statistical outlier, using the
    median absolute deviation (MAD) modified z-score computed WITHIN each
    board/link_mode's own group of sketches.
    """

    by_board = defaultdict(list)
    for record in records:
        by_board[(record["board"], record["link_mode"])].append(record)

    outliers = []
    for group in by_board.values():
        values = [r[key] for r in group]
        median = statistics.median(values)
        mad = statistics.median(abs(v - median) for v in values)
        for record in group:
            value = record[key]
            if mad == 0:
                # every non-outlier record in this board shares the exact
                # same value: anything else stands out regardless of score
                is_outlier = value != median
                score = None
            else:
                score = 0.6745 * (value - median) / mad
                is_outlier = abs(score) > threshold
            if is_outlier:
                outliers.append({**record, "board_median": median, "mad_score": score})
    return outliers

def build_trends(input_dir):
    """
    Load all report records from input_dir and compute the trends summary.
    """

    records = load_records(input_dir)
    return {
        "record_count": len(records),
        "flash_outliers": mad_outliers(records, "flash_delta_abs"),
        "ram_outliers": mad_outliers(records, "ram_delta_abs"),
    }, records

def main():
    parser = argparse.ArgumentParser(
        description="Extract trends and flag outliers from ci_calc_size_reports.py delta reports")
    parser.add_argument("--input-dir", default=".",
                         help="directory containing delta report JSON files (default: current directory)")
    parser.add_argument("--output-json",
                         help="write the trends summary as JSON to this path (default: print to stdout)")
    args = parser.parse_args()

    trends, _ = build_trends(args.input_dir)
    output = json.dumps(trends, indent=2)

    if args.output_json:
        Path(args.output_json).write_text(output)
        print(f"Wrote trends JSON to {args.output_json}")
    else:
        print(output)

if __name__ == "__main__":
    main()
