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
from collections import Counter, defaultdict
import html
import io
import json
from pathlib import Path
import re
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

class _Safe(str):
    """A table cell that is already-safe HTML and must not be escaped again."""

class _Cell:
    """A table cell with an optional inline style (e.g. a background color)."""

    def __init__(self, text, style=None):
        self.text = text
        self.style = style

# same hue as the chart backgrounds added later (pale green below zero, pale
# red above); gray marks a value that falls below the MIN_DELTA threshold
NEGATIVE_CELL_STYLE = "background-color: rgba(46, 160, 44, 0.35);"
POSITIVE_CELL_STYLE = "background-color: rgba(214, 39, 40, 0.35);"
NEUTRAL_CELL_STYLE = "background-color: rgba(136, 136, 136, 0.3);"

def _mono(text):
    """Render a package/board identifier in a typewriter (monospace) font."""

    return _Safe(f"<code>{html.escape(str(text))}</code>")

def _board_name(text):
    """Render a board name bold and in a typewriter (monospace) font."""

    return _Safe(f"<strong><code>{html.escape(str(text))}</code></strong>")

def _bold_board_label(label):
    """Bold+monospace just the board name portion of a "board (link_mode)" label."""

    match = re.match(r"^(.*) \((\w+)\)$", label)
    if not match:
        return html.escape(label)
    board, link_mode = match.groups()
    return f"<strong><code>{html.escape(board)}</code></strong> ({html.escape(link_mode)})"

def _delta_cell(value, text=None):
    """
    A delta-value cell shaded green/red by sign, or gray if the value falls
    below the MIN_DELTA threshold (including exactly zero). Positive values
    are shown with an explicit "+" sign, matching the Markdown report.
    """

    if abs(value) < MIN_DELTA:
        style = NEUTRAL_CELL_STYLE
    elif value < 0:
        style = NEGATIVE_CELL_STYLE
    else:
        style = POSITIVE_CELL_STYLE
    if text is None:
        text = f"{value:+d}" if value != 0 else "0"
    return _Cell(text, style)

def _render_td(cell):
    if isinstance(cell, _Cell):
        text = str(cell.text) if isinstance(cell.text, _Safe) else html.escape(str(cell.text))
        style = f' style="{cell.style}"' if cell.style else ""
        return f"<td{style}>{text}</td>"
    text = str(cell) if isinstance(cell, _Safe) else html.escape(str(cell))
    return f"<td>{text}</td>"

_NO_ROWS_MESSAGE = "<p><em>none</em></p>"

def _html_table(headers, rows):
    if not rows:
        return _NO_ROWS_MESSAGE
    head = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(_render_td(cell) for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

def _html_table_grouped(solo_headers, group_headers, sub_headers, rows):
    """
    A table with a two-row header: solo_headers span both header rows
    (e.g. "board"), and each name in group_headers spans len(sub_headers)
    columns in the top row, with sub_headers repeated underneath it (e.g.
    "Flash" / "RAM", each split into "min" / "mean" / "median" / "max").
    """

    if not rows:
        return _NO_ROWS_MESSAGE

    row1 = "".join(f'<th rowspan="2">{html.escape(h)}</th>' for h in solo_headers)
    row1 += "".join(f'<th colspan="{len(sub_headers)}">{html.escape(g)}</th>' for g in group_headers)
    row2 = "".join(f"<th>{html.escape(h)}</th>" for h in sub_headers * len(group_headers))

    body = "".join(
        "<tr>" + "".join(_render_td(cell) for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{row1}</tr><tr>{row2}</tr></thead><tbody>{body}</tbody></table>"

def _figure_to_inline_svg(fig, plt, bold_mono_labels=(), tooltips=None):
    """
    Render a matplotlib figure to inline SVG markup (real <text>/<circle>/
    <path> elements, not baked-in glyph outlines or a raster image), so it
    can be embedded directly in an HTML report with no external files and
    no JavaScript.

    bold_mono_labels: tick-label strings of the form "name (mode)" whose
    "name" portion should render bold+monospace while " (mode)" stays in
    the chart's normal font — matching the board/link_mode split styling
    used elsewhere in the HTML tables. matplotlib text has no per-run
    styling, and SVG has no inline HTML either, but SVG's own equivalent
    (<tspan>, mixing styles within one <text> element) does the same job,
    so the label's exact text content is swapped for a <tspan>-wrapped
    version after rendering.

    tooltips: {gid: text} for artists whose set_gid(gid) was called before
    rendering (e.g. one scatter() call per point). matplotlib wraps each
    such artist in <g id="gid">...</g>; a <title> inserted as its first
    child gives it a native hover tooltip, no JavaScript needed, same as
    the "title" attribute would in plain HTML.
    """

    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    svg = buf.getvalue().decode("utf-8")
    svg = svg[svg.index("<svg"):]

    # matplotlib resolves "system-ui"/"monospace" to a long quoted fallback
    # chain for its own local rendering and writes that verbatim into the
    # SVG's CSS; browsers treat a *quoted* 'system-ui' as a literal (and
    # nonexistent) font name rather than the special unquoted keyword, so
    # rewrite both chains down to the plain generic keywords that actually
    # match the surrounding HTML page's font instead of matplotlib's
    # locally-installed fallback fonts.
    svg = re.sub(r"font-family: [^;]*sans-serif;", "font-family: system-ui, sans-serif;", svg)
    svg = re.sub(r"font-family: [^;]*monospace;", "font-family: monospace;", svg)

    for label in bold_mono_labels:
        match = re.match(r"^(.*) \((\w+)\)$", label)
        if not match:
            continue
        board, mode = match.groups()
        old = f">{html.escape(label)}<"
        new = (f'><tspan style="font-weight:bold;font-family:monospace">'
               f'{html.escape(board)}</tspan> ({html.escape(mode)})<')
        svg = svg.replace(old, new)

    for gid, text in (tooltips or {}).items():
        svg = re.sub(
            rf'(<g id="{re.escape(gid)}"[^>]*>)',
            rf'\1<title>{html.escape(text)}</title>',
            svg, count=1,
        )

    return _Safe(svg)

def _chart_bubble(records, key, label, plt, min_abs_delta=MIN_DELTA):
    """
    Bubble chart of one metric's delta distribution, one row per
    board/link_mode that has at least one delta reaching min_abs_delta,
    ordered by that board's largest delta (descending) so the most notable
    boards group at the top. Each bubble's x position is a delta value
    actually seen on that board, and its size encodes how many sketches on
    that board share that exact value. Boards with no delta reaching the
    threshold are left out of the plot entirely; instead, a text summary
    grouping those boards by their typical (median) delta is returned
    alongside the chart, so the report is not padded with empty rows.

    Returns (inline_svg_markup_or_None, excluded_rows).
    """

    all_values = defaultdict(list)
    qualifying = defaultdict(list)
    for record in records:
        board_label = f"{record['board']} ({record['link_mode']})"
        value = record[key]
        all_values[board_label].append(value)
        if abs(value) >= min_abs_delta:
            qualifying[board_label].append(value)

    plotted_boards = sorted(
        qualifying.keys(),
        key=lambda l: (-max(abs(v) for v in qualifying[l]), l),
    )
    excluded_boards = sorted(set(all_values) - set(qualifying))

    img = None
    if plotted_boards:
        xs, ys, counts = [], [], []
        for row, board_label in enumerate(plotted_boards):
            for value, count in Counter(qualifying[board_label]).items():
                xs.append(value)
                ys.append(row)
                counts.append(count)
        max_count = max(counts)
        sizes = [30 + 220 * (count / max_count) for count in counts]
        colors = ["#888888" if v == 0 else "#217821" if v < 0 else "#a31f1f" for v in xs]

        fig, ax = plt.subplots(figsize=(9, max(3, 0.4 * len(plotted_boards))))
        # one scatter() call per point (instead of one batched call for all
        # of them) so each bubble gets its own gid, letting the SVG
        # post-processing below give it its own hover tooltip
        tooltips = {}
        for i, (x_val, y_val, size, color, count, board_label) in enumerate(
            zip(xs, ys, sizes, colors, counts, (plotted_boards[y] for y in ys))
        ):
            gid = f"bubble-{label}-{i}"
            ax.scatter([x_val], [y_val], s=[size], color=color, alpha=0.85,
                       edgecolors="#333333", linewidths=0.5, zorder=3, gid=gid)
            sketch_word = "sketch" if count == 1 else "sketches"
            tooltips[gid] = f"{board_label}: {x_val:+d} bytes ({count} {sketch_word})"
        for x_val, y_val in zip(xs, ys):
            ax.annotate(f"{x_val:+d}", (x_val, y_val), xytext=(0, -8), textcoords="offset points",
                        ha="center", va="top", fontsize=6, color="#333333", zorder=4)

        ax.set_yticks(range(len(plotted_boards)))
        ax.set_yticklabels(plotted_boards)
        ax.set_ylim(len(plotted_boards) - 0.5, -0.5)

        # use the actual data extent, not ax.get_xlim(): matplotlib's linear
        # autoscale already adds its own default margin (~5% of the *total*
        # span) to both sides, which on lopsided data inflates the small
        # side's bound far more (in ratio terms) than the large side's
        data_min = min(xs + [0])
        data_max = max(xs + [0])
        # multiplicative pad, not additive: on a log-ish axis, equal visual
        # margin means equal *ratio*, so both sides are scaled by the same
        # factor regardless of how differently sized their magnitudes are
        pad_ratio = 1.3
        left = data_min * pad_ratio if data_min < 0 else -min_abs_delta * pad_ratio
        right = data_max * pad_ratio if data_max > 0 else min_abs_delta * pad_ratio
        xlim = (left, right)
        ax.axvspan(xlim[0], -min_abs_delta, color="#2ca02c", alpha=0.18, zorder=0)
        ax.axvspan(min_abs_delta, xlim[1], color="#d62728", alpha=0.18, zorder=0)
        ax.axvspan(-min_abs_delta, min_abs_delta, color="#888888", alpha=0.25, zorder=0.5)
        ax.set_xlim(xlim)
        # symlog, not log: deltas can be negative or zero, and every plotted
        # point already clears min_abs_delta, so the linear region just
        # covers the (empty) noise band without needing to render it
        ax.set_xscale("symlog", linthresh=min_abs_delta, linscale=0.3)
        # "10k"/"1M" instead of matplotlib's default "10^4"/"10^6" tick labels
        from matplotlib.ticker import EngFormatter
        ax.xaxis.set_major_formatter(EngFormatter(sep=""))

        ax.axvline(0, color="#999", linewidth=0.8, linestyle="--", zorder=1)
        ax.set_xlabel(f"{label} delta (bytes, |delta| >= {min_abs_delta})")
        ax.set_title(f"{label} delta distribution per board / link_mode, sorted by delta magnitude "
                      "(bubble size = number of matching sketches)")
        fig.tight_layout()
        img = _figure_to_inline_svg(fig, plt, bold_mono_labels=plotted_boards, tooltips=tooltips)

    by_value = defaultdict(list)
    for board_label in excluded_boards:
        median_value = _truncate(statistics.median(all_values[board_label]))
        by_value[median_value].append(board_label)

    def value_label(value):
        return "unchanged" if value == 0 else f"{value:+d}"

    excluded_rows = [
        (_delta_cell(value, text=value_label(value)), _Safe(", ".join(_bold_board_label(b) for b in boards)))
        for value, boards in sorted(by_value.items())
    ]

    return img, excluded_rows

def generate_html(report_data, records):
    """
    Render prepared report data as a single self-contained HTML page: charts
    are rendered with matplotlib as inline SVG, so the output file has no
    external dependencies, no JavaScript, and can be opened/shared as-is.
    """

    import logging
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["svg.fonttype"] = "none"
    matplotlib.rcParams["font.family"] = "system-ui, sans-serif"
    import matplotlib.pyplot as plt

    flash_box_img, flash_box_excluded = _chart_bubble(records, "flash_delta_abs", "Flash", plt)
    ram_box_img, ram_box_excluded = _chart_bubble(records, "ram_delta_abs", "RAM", plt)

    board_rows = [
        (_mono(row[0]), _board_name(row[1]), row[2], row[3], *(_delta_cell(v) for v in row[4:]))
        for row in report_data["board_rows"]
    ]
    flash_outlier_rows = [
        (_board_name(board), link_mode, sketch, _delta_cell(flash), _delta_cell(ram))
        for board, link_mode, sketch, flash, ram in report_data["flash_outlier_rows"]
    ]
    ram_outlier_rows = [
        (_board_name(board), link_mode, sketch, _delta_cell(flash), _delta_cell(ram))
        for board, link_mode, sketch, flash, ram in report_data["ram_outlier_rows"]
    ]
    trend_rows = [
        (sketch, _board_name(board), link_mode, _delta_cell(flash), _delta_cell(ram))
        for sketch, board, link_mode, flash, ram in report_data["trend_rows"]
    ]

    top_n = report_data["top_n"]

    def top_suffix(total):
        return f" (top {top_n} of {total})" if top_n < total else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Size delta trends report</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #222; }}
  h1, h2 {{ border-bottom: 1px solid #ddd; padding-bottom: .3rem; }}
  table {{ border-collapse: collapse; margin: 1rem 0 2rem; font-size: .85rem; border: 2px solid #666; }}
  th, td {{ border: 1px solid #888; padding: .3rem .6rem; text-align: right; }}
  th {{ background: #f2f2f2; }}
  td:nth-child(-n+3), th:nth-child(-n+3) {{ text-align: left; }}
  img {{ max-width: 100%; height: auto; margin: .5rem 0; }}
  .summary {{ color: #555; }}
</style>
</head>
<body>
<h1>Size delta trends report</h1>
<p class="summary">{report_data["record_count"]} sketch/board/link_mode records across
{report_data["n_board_groups"]} board/link_mode combinations.
{report_data["n_flash_outliers"]} flash and {report_data["n_ram_outliers"]} RAM per-board outliers flagged.
</p>

<h2>Per-board delta distributions</h2>
{flash_box_img or ""}
<p class="summary">Boards below the {MIN_DELTA} byte threshold (not plotted above):</p>
{_html_table(["delta", "boards"], flash_box_excluded)}
{ram_box_img or ""}
<p class="summary">Boards below the {MIN_DELTA} byte threshold (not plotted above):</p>
{_html_table(["delta", "boards"], ram_box_excluded)}

<h2>Per-board / link_mode summary</h2>
{_html_table_grouped(["package", "board", "link_mode", "sketches"], ["Flash", "RAM"],
                      ["min", "mean", "median", "max"], board_rows)}

<h2>Flash delta outliers{top_suffix(report_data["n_flash_outliers"])}</h2>
{_html_table(["board", "link_mode", "sketch", "flash Δ", "RAM Δ"], flash_outlier_rows)}

<h2>RAM delta outliers{top_suffix(report_data["n_ram_outliers"])}</h2>
{_html_table(["board", "link_mode", "sketch", "flash Δ", "RAM Δ"], ram_outlier_rows)}

<h2>Outlier sketches across boards</h2>
<p class="summary">Full per-board pattern for every sketch flagged above, showing
whether the anomaly is isolated to one board or a wider trend.</p>
{_html_table(["sketch", "board", "link_mode", "flash Δ", "RAM Δ"], trend_rows)}
</body>
</html>
"""

def main():
    parser = argparse.ArgumentParser(
        description="Extract trends and flag outliers from ci_calc_size_reports.py delta reports")
    parser.add_argument("--input-dir", default=".",
                         help="directory containing delta report JSON files (default: current directory)")
    parser.add_argument("--output-json",
                         help="write the trends summary as JSON to this path (default: print to stdout "
                              "if --output-html is not given either)")
    parser.add_argument("--output-html",
                         help="write a self-contained HTML report (charts + tables, no external assets) "
                              "to this path; requires matplotlib")
    args = parser.parse_args()

    trends, records = build_trends(args.input_dir)

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(trends, indent=2))
        print(f"Wrote trends JSON to {args.output_json}")
    elif not args.output_html:
        print(json.dumps(trends, indent=2))

    if args.output_html:
        report_data = _build_report_data(trends, top_n=30)
        Path(args.output_html).write_text(generate_html(report_data, records))
        print(f"Wrote trends HTML report to {args.output_html}")

if __name__ == "__main__":
    main()
