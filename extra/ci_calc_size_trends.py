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

def _read_commit_info(input_dir):
    """
    Read the (head_sha, head_url) the reports were generated for, from the
    first report JSON file found. All files in one CI run describe the
    same commit, so any one file's values are representative.
    """

    for path in sorted(Path(input_dir).glob("*.json")):
        with open(path) as f:
            data = json.load(f)
        return data.get("commit_hash"), data.get("commit_url")
    return None, None

def build_trends(input_dir):
    """
    Load all report records from input_dir and compute the full trends
    summary: per-board outliers, per-board summary, and cross-board outlier
    trends.
    """

    records = load_records(input_dir)
    head_sha, head_url = _read_commit_info(input_dir)
    flash_outliers = mad_outliers(records, "flash_delta_abs")
    ram_outliers = mad_outliers(records, "ram_delta_abs")
    return {
        "head_sha": head_sha,
        "head_url": head_url,
        "record_count": len(records),
        "board_summary": per_board_summary(records),
        "flash_outliers": flash_outliers,
        "ram_outliers": ram_outliers,
        "outlier_sketch_trends": outlier_sketch_trends(records, flash_outliers, ram_outliers),
    }, records

def _truncate(value):
    """Truncate a byte-size value to an integer for display."""

    return int(value)

def _base_url(head_url, base_sha):
    """
    Derive the base commit's URL from the head commit's URL (same repo,
    GitHub's .../commit/<sha> pattern), so the base is also a link
    whenever we have enough information to build one.
    """

    if not head_url or not base_sha:
        return None
    return head_url.rsplit("/", 1)[0] + "/" + base_sha

def _compare_url(head_url, base_sha, head_sha):
    """
    Build a GitHub compare view URL between base_sha and head_sha, derived
    from the head commit's URL the same way _base_url derives the base
    commit's own link.
    """

    if not head_url or not base_sha or not head_sha:
        return None
    repo_url = head_url.rsplit("/", 2)[0]
    return f"{repo_url}/compare/{base_sha}...{head_sha}"

def _outlier_rows(outliers, top_n):
    """Rank outlier records by combined magnitude and return the top N as plain tuples."""

    ranked = sorted(outliers, key=lambda o: -(abs(o["flash_delta_abs"]) + abs(o["ram_delta_abs"])))
    return [
        (o["board"], o["link_mode"], o["sketch"],
         _truncate(o["flash_delta_abs"]), _truncate(o["ram_delta_abs"]))
        for o in ranked[:top_n]
    ]

def _build_report_data(trends, top_n, base_sha=None):
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
        "head_sha": trends["head_sha"],
        "head_url": trends["head_url"],
        "base_sha": base_sha,
        "base_url": _base_url(trends["head_url"], base_sha),
        "compare_url": _compare_url(trends["head_url"], base_sha, trends["head_sha"]),
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

def _commit_html(sha, url):
    """Render a commit as a short linked hash, or "unknown" if absent."""

    if not sha:
        return "unknown"
    short = html.escape(sha[:10])
    return f'<a href="{html.escape(url)}"><code>{short}</code></a>' if url else f"<code>{short}</code>"

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

        # mean and 1-sigma window over EVERY sketch on that board (not just
        # the ones clearing min_abs_delta), matching the population that
        # per_board_summary()/mad_outliers() already summarize elsewhere
        row_stats = {}
        for row, board_label in enumerate(plotted_boards):
            values = all_values[board_label]
            mean = statistics.mean(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 0.0
            row_stats[row] = (mean, stdev)

        for row, (mean, stdev) in row_stats.items():
            ax.fill_betweenx([row - 0.4, row + 0.4], mean - stdev, mean + stdev,
                              color="#add8e6", alpha=0.4, zorder=1,
                              label="mean ± σ" if row == 0 else None)
            ax.plot([mean, mean], [row - 0.4, row + 0.4], linewidth=1.5,
                    color="#1f4e79", zorder=2,
                    label="mean" if row == 0 else None)
        ax.legend(loc="lower right", fontsize=7, frameon=False)

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
        ax.set_title(f"{label} delta distribution per board / link_mode")
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

def _accordion(group_name, items):
    """
    Render (label, table_html) pairs as a set of <details name="group_name">
    elements. Sharing one `name` across a group of <details> is native
    HTML: the browser keeps at most one of them open at a time within that
    name, with no JavaScript required.
    """

    def render_label(label):
        return str(label) if isinstance(label, _Safe) else html.escape(str(label))

    return "\n\n".join(
        f'<details name="{group_name}">\n<summary>{render_label(label)}</summary>\n\n{table_html}\n\n</details>'
        for label, table_html in items
    )

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

    head_html = _commit_html(report_data["head_sha"], report_data["head_url"])
    base_html = _commit_html(report_data["base_sha"], report_data["base_url"])
    compare_html = f' (<a href="{html.escape(report_data["compare_url"])}">compare</a>)' if report_data["compare_url"] else ""

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

    raw_by_board = defaultdict(list)
    raw_by_sketch = defaultdict(list)
    for record in records:
        raw_by_board[(record["package"], record["board"], record["link_mode"])].append(record)
        raw_by_sketch[record["sketch"]].append(record)

    def notable_counts(recs):
        """
        Count notable (not ignored, i.e. clears MIN_DELTA) flash/RAM values
        in recs, split by sign: negative (green) vs. positive (red).
        """

        green = red = 0
        for r in recs:
            for key in ("flash_delta_abs", "ram_delta_abs"):
                value = r[key]
                if value >= MIN_DELTA:
                    red += 1
                elif value <= -MIN_DELTA:
                    green += 1
        return green, red

    def _count_dot(count, color):
        return (f'{count}<span style="display:inline-block;width:.6em;height:.6em;border-radius:50%;'
                f'background:{color};margin:0 .1em 0 .1em;vertical-align:middle;"></span>')

    def notable_suffix(recs):
        green, red = notable_counts(recs)
        parts = []
        if green:
            parts.append(_count_dot(green, "#217821"))
        if red:
            parts.append(_count_dot(red, "#a31f1f"))
        return f' ({", ".join(parts)})' if parts else ""

    def board_table_items():
        for (package, board, link_mode), recs in sorted(raw_by_board.items()):
            recs = sorted(recs, key=lambda r: r["sketch"])
            rows = [
                (_mono(r["sketch"]), _delta_cell(_truncate(r["flash_delta_abs"])),
                 _delta_cell(_truncate(r["ram_delta_abs"])))
                for r in recs
            ]
            label = _Safe(
                f"{_mono(package)} {_board_name(board)} ({html.escape(link_mode)}) "
                f"- {len(rows)} sketches{notable_suffix(recs)}"
            )
            yield label, _html_table(["sketch", "flash Δ", "RAM Δ"], rows)

    def sketch_table_items():
        for sketch, recs in sorted(raw_by_sketch.items()):
            recs = sorted(recs, key=lambda r: (r["board"], r["link_mode"]))
            rows = [
                (_board_name(r["board"]), r["link_mode"], _delta_cell(_truncate(r["flash_delta_abs"])),
                 _delta_cell(_truncate(r["ram_delta_abs"])))
                for r in recs
            ]
            label = _Safe(f"{_mono(sketch)} - {len(rows)} boards{notable_suffix(recs)}")
            yield label, _html_table(["board", "link_mode", "flash Δ", "RAM Δ"], rows)

    board_tables = _accordion("board-details", board_table_items())
    sketch_tables = _accordion("sketch-details", sketch_table_items())

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
<h1>Size deltas from {base_html} to {head_html}{compare_html}</h1>
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

<h2>Per-board delta tables</h2>
<p class="summary">Every sketch's flash/RAM delta on that board/link_mode. Opening one closes any other open here.</p>
{board_tables}

<h2>Per-sketch delta tables</h2>
<p class="summary">Every board/link_mode a sketch was built for, and its flash/RAM delta there. Opening one closes any other open here.</p>
{sketch_tables}
</body>
</html>
"""

def _md_code(text):
    """Render a package/board identifier in a typewriter (monospace) font."""

    return f"`{text}`"

def _md_number(value):
    """
    Bold a delta value if its magnitude clears the MIN_DELTA threshold, and
    prefix it with a small colored dot by sign (green for negative, red for
    positive). Values that don't clear the threshold are ignored deltas:
    plain, unmarked numbers, so the dot only ever flags a genuinely notable
    value. GitHub is the only Markdown renderer this targets, so nested
    <sub>/<sup> is safe to rely on; it also shrinks and vertically centers
    the circle so it renders as a small dot instead of a full-size emoji
    that skews table row height.
    """

    text = f"{value:+d}" if value != 0 else "0"
    if abs(value) <= MIN_DELTA:
        return text
    marker = "<sub><sup>🟢</sup></sub>" if value < 0 else "<sub><sup>🔴</sup></sub>"
    return f"{marker}&nbsp;**{text}**"

def _commit_md(sha, url):
    """Render a commit as a short linked hash, or "unknown" if absent."""

    if not sha:
        return "unknown"
    short = sha[:10]
    return f"[`{short}`]({url})" if url else f"`{short}`"

def _markdown_table(headers, rows, align=None):
    """
    align is an optional per-column list of "l"/"r" (default all "l");
    "r" right-aligns a numeric column via the GFM `---:` separator syntax.
    """

    if not rows:
        return "_none_"
    if align is None:
        align = ["l"] * len(headers)
    sep_cell = {"l": "---", "r": "---:"}
    lines = [
        "| " + " | ".join(str(h) for h in headers) + " |",
        "| " + " | ".join(sep_cell[a] for a in align) + " |",
    ]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)

def generate_markdown(report_data):
    """
    Render prepared report data as a GitHub-flavored Markdown report: a
    one-line count recap, the outlier-sketch cross-board trend table, the
    per-board summary rows with at least one notable (>= MIN_DELTA) value,
    and the full per-board summary folded into a collapsed section.
    """

    board_headers = ["package", "board", "link_mode", "sketches",
                      "flash min", "flash mean", "flash median", "flash max",
                      "ram min", "ram mean", "ram median", "ram max"]
    board_align = ["l", "l", "l"] + ["r"] * (len(board_headers) - 3)
    trend_align = ["l", "l", "l", "r", "r"]

    def format_board_row(row):
        package, board, link_mode, sketch_count, *deltas = row
        return (_md_code(package), _md_code(board), link_mode, sketch_count,
                *(_md_number(v) for v in deltas))

    raw_board_rows = report_data["board_rows"]
    notable_raw_rows = [row for row in raw_board_rows if any(abs(v) >= MIN_DELTA for v in row[4:])]
    notable_board_rows = [format_board_row(row) for row in notable_raw_rows]

    by_package = defaultdict(list)
    for raw_row in raw_board_rows:
        by_package[raw_row[0]].append(format_board_row(raw_row)[1:])

    full_sections = "\n\n".join(
        f"<details>\n<summary>Full per-board/link-mode summary for {_mono(package)}</summary>\n\n"
        f"{_markdown_table(board_headers[1:], rows, board_align[1:])}\n\n</details>"
        for package, rows in by_package.items()
    )

    trend_rows = [
        (sketch, _md_code(board), link_mode, _md_number(flash), _md_number(ram))
        for sketch, board, link_mode, flash, ram in report_data["trend_rows"]
    ]

    def short_sha(sha):
        return sha[:10] if sha else "unknown"

    head_sha = short_sha(report_data["head_sha"])
    base_sha = short_sha(report_data["base_sha"])
    compare_suffix = f' ([compare]({report_data["compare_url"]}))' if report_data["compare_url"] else ""

    recap = (
        f'{report_data["record_count"]} sketch/board/link_mode records across '
        f'{report_data["n_board_groups"]} board/link_mode combinations. '
        f'{report_data["n_flash_outliers"]} flash and {report_data["n_ram_outliers"]} RAM per-board '
        "outliers flagged."
    )

    return f"""
---

## Size deltas from {base_sha} to {head_sha}{compare_suffix}

{recap}

## Per-board / link_mode summary

{_markdown_table(board_headers, notable_board_rows, board_align)}

{full_sections}

## Outlier sketches across boards

{_markdown_table(["sketch", "board", "link_mode", "flash Δ", "RAM Δ"], trend_rows, trend_align)}
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
    parser.add_argument("--output-md",
                         help="write a GitHub-flavored Markdown report (counts recap, outlier tables, "
                              "per-board summary) to this path")
    parser.add_argument("--base-sha",
                         help="SHA of the baseline commit the deltas were computed against (the "
                              "reports themselves don't record it); shown in the HTML/Markdown "
                              "report header alongside the commit they were generated for")
    args = parser.parse_args()

    trends, records = build_trends(args.input_dir)

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(trends, indent=2))
        print(f"Wrote trends JSON to {args.output_json}")
    elif not args.output_html and not args.output_md:
        print(json.dumps(trends, indent=2))

    if args.output_html or args.output_md:
        report_data = _build_report_data(trends, top_n=30, base_sha=args.base_sha)
        if args.output_html:
            Path(args.output_html).write_text(generate_html(report_data, records))
            print(f"Wrote trends HTML report to {args.output_html}")
        if args.output_md:
            Path(args.output_md).write_text(generate_markdown(report_data))
            print(f"Wrote trends Markdown report to {args.output_md}")

if __name__ == "__main__":
    main()
