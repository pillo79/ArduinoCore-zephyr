#!/usr/bin/env python3

# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# Script to extract trends and flag outliers from the delta reports produced
# by extra/ci_calc_size_reports.py.
#
# This script expects a directory of "<package>-<board>-link_mode=<mode>.json"
# report files (each already annotated with per-sketch "delta" data) and
# prints/writes a JSON summary of:
#  - per-board/link_mode delta distributions (boards are not comparable to
#    one another, so all statistics are computed within each board's own
#    group of sketches, never across the whole dataset)
#  - sketches whose delta is a statistical outlier vs. its own board's
#    distribution
#  - cross-board and static/dynamic link_mode trends

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

SIZE_NAMES = ("flash", "RAM for global variables")

# deltas smaller than this (in bytes) are treated as noise: common
# per-binary overhead changes that would otherwise dominate a report
# without being interesting
MIN_DELTA = 128

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

def per_board_summary(records):
    """
    Summarize flash/RAM deltas per (package, board, link_mode) group.
    """

    by_board = defaultdict(list)
    for record in records:
        by_board[(record["package"], record["board"], record["link_mode"])].append(record)

    summary = []
    for (package, board, link_mode), group in sorted(by_board.items()):
        flash_vals = [r["flash_delta_abs"] for r in group]
        ram_vals = [r["ram_delta_abs"] for r in group]
        summary.append({
            "package": package,
            "board": board,
            "link_mode": link_mode,
            "sketch_count": len(group),
            "flash_delta_min": min(flash_vals),
            "flash_delta_mean": statistics.mean(flash_vals),
            "flash_delta_median": statistics.median(flash_vals),
            "flash_delta_max": max(flash_vals),
            "ram_delta_min": min(ram_vals),
            "ram_delta_mean": statistics.mean(ram_vals),
            "ram_delta_median": statistics.median(ram_vals),
            "ram_delta_max": max(ram_vals),
        })
    return summary

def outlier_sketch_trends(records, flash_outliers, ram_outliers):
    """
    For every sketch that was flagged as a flash or RAM outlier on at least
    one board, list its delta on every board/link_mode it appears on. This
    shows whether a flagged anomaly is isolated to one board or a wider
    cross-board trend, without dumping every sketch's minor per-board
    variation (most of which is not an outlier, just normal board-specific
    noise).
    """

    flagged_sketches = {o["sketch"] for o in flash_outliers} | {o["sketch"] for o in ram_outliers}
    if not flagged_sketches:
        return []

    by_sketch = defaultdict(list)
    for record in records:
        if record["sketch"] in flagged_sketches:
            by_sketch[record["sketch"]].append(record)

    trends = []
    for sketch, group in by_sketch.items():
        entries = sorted(
            ({"board": r["board"], "link_mode": r["link_mode"],
              "flash_delta_abs": r["flash_delta_abs"], "ram_delta_abs": r["ram_delta_abs"]}
             for r in group),
            key=lambda e: (e["board"], e["link_mode"]),
        )
        trends.append({
            "sketch": sketch,
            "entries": entries,
            "max_abs_delta": max(abs(e["flash_delta_abs"]) + abs(e["ram_delta_abs"]) for e in entries),
        })

    trends.sort(key=lambda t: -t["max_abs_delta"])
    return trends

def build_trends(input_dir):
    """
    Load all report records from input_dir and compute the full trends
    summary: per-board outliers, per-board summary, and cross-board outlier
    trends.
    """

    records = load_records(input_dir)
    flash_outliers = mad_outliers(records, "flash_delta_abs")
    ram_outliers = mad_outliers(records, "ram_delta_abs")
    return {
        "record_count": len(records),
        "board_summary": per_board_summary(records),
        "flash_outliers": flash_outliers,
        "ram_outliers": ram_outliers,
        "outlier_sketch_trends": outlier_sketch_trends(records, flash_outliers, ram_outliers),
    }, records

def _truncate(value):
    """Truncate a byte-size value to an integer for display."""

    return int(value)

def _outlier_rows(outliers, top_n):
    """Rank outlier records by combined magnitude and return the top N as plain tuples."""

    ranked = sorted(outliers, key=lambda o: -(abs(o["flash_delta_abs"]) + abs(o["ram_delta_abs"])))
    return [
        (o["board"], o["link_mode"], o["sketch"],
         _truncate(o["flash_delta_abs"]), _truncate(o["ram_delta_abs"]))
        for o in ranked[:top_n]
    ]

def _build_report_data(trends, top_n):
    """
    Assemble every prepared row set needed for a report, as plain Python
    values with no markup of any kind. Keeping this decoupled from any
    particular output format means a renderer for a different format (e.g.
    Markdown) could reuse the exact same rows instead of re-deriving them.
    """

    board_rows = [
        (b["package"], b["board"], b["link_mode"], b["sketch_count"],
         _truncate(b["flash_delta_min"]), _truncate(b["flash_delta_mean"]),
         _truncate(b["flash_delta_median"]), _truncate(b["flash_delta_max"]),
         _truncate(b["ram_delta_min"]), _truncate(b["ram_delta_mean"]),
         _truncate(b["ram_delta_median"]), _truncate(b["ram_delta_max"]))
        for b in trends["board_summary"]
    ]

    trend_rows = [
        (t["sketch"], e["board"], e["link_mode"],
         _truncate(e["flash_delta_abs"]), _truncate(e["ram_delta_abs"]))
        for t in trends["outlier_sketch_trends"][:top_n]
        for e in t["entries"]
        if abs(e["flash_delta_abs"]) >= MIN_DELTA or abs(e["ram_delta_abs"]) >= MIN_DELTA
    ]

    return {
        "record_count": trends["record_count"],
        "n_board_groups": len(trends["board_summary"]),
        "n_flash_outliers": len(trends["flash_outliers"]),
        "n_ram_outliers": len(trends["ram_outliers"]),
        "top_n": top_n,
        "board_rows": board_rows,
        "flash_outlier_rows": _outlier_rows(trends["flash_outliers"], top_n),
        "ram_outlier_rows": _outlier_rows(trends["ram_outliers"], top_n),
        "trend_rows": trend_rows,
    }

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
