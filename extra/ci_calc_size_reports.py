#!/usr/bin/env python3

# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# Script to calculate the size deltas of the current CI test reports against
# the most recent test results of the base branch, in the official JSON report
# format.
#
# This scripts expects the following arguments:
#  - <base_branch>: branch whose latest test results are used as reference
#  - <reports_folder>: directory to populate with the delta reports
#
# The script performs the following actions:
# - downloads the latest test results of the base branch from ci-builds (the
#   most recent daily or push test run, see ci_pack_test_results.sh)
# - for each JSON report file in the current directory that has a valid
#   reference, writes a copy with the delta information in the output folder.

from collections import defaultdict
import copy
import glob
import json
import os
import requests
import re
import sys

REFERENCE_URL = "https://pillo79.github.io/ci-builds/snippets/pillo79/ArduinoCore-zephyr/{}/latest/test_info.json" # TEMP (fork test)

def update_final_deltas(final, abs_max, delta):
    """
    Update the final delta values for a given entry (e.g. "flash" or "RAM for
    global variables") based on a new delta calculation from a sketch.
    """

    if not "maximum" in final:
        final["maximum"] = abs_max
        final["delta"] = {}
        for key in delta: # rel/abs
            val = delta[key]
            final["delta"][key] = {
                "minimum": val,
                "maximum": val
            }
    else:
        final["maximum"] = max(final["maximum"], abs_max)
        for key in delta: # rel/abs
            val = delta[key]
            final["delta"][key]["minimum"] = min(final["delta"][key]["minimum"], val)
            final["delta"][key]["maximum"] = max(final["delta"][key]["maximum"], val)

def range_str(delta):
    """
    Format a delta value (with "absolute" and "relative" keys) as a string for
    display in the summary table.
    """

    if not delta:
        return "N/A"

    dmin = delta['absolute']['minimum']
    dmax = delta['absolute']['maximum']
    if not dmin and not dmax:
        return "==="

    dmin_str = f"{int(dmin)}" if dmin <= 0 else f"+{int(dmin)}"
    dmax_str = f"{int(dmax)}" if dmax <= 0 else f"+{int(dmax)}"
    if dmin == dmax:
        return dmin_str
    else:
        return f"{dmin_str}..{dmax_str}"

if not len(sys.argv) == 3:
    print("Usage: ci_calc_size_reports.py <base_branch> <output_folder>")
    sys.exit(1)

base_branch = sys.argv[1]
output_folder = sys.argv[2]

# get the latest test results of the base branch
response = requests.get(REFERENCE_URL.format(base_branch))
if response.status_code == 404:
    print(f"::notice::No test results available for '{base_branch}', size deltas not computed")
    sys.exit(0)
response.raise_for_status()
reference = response.json()
old_reports = reference['reports'] # { fqbn: board report }
print(f"Reference: {reference['event']} test of {reference['core_version']} ({reference['timestamp']})")

headers = [ "Package",  "Board",    "Options",  "Flash",    " RAM ",    "Tests",    f"vs {reference['event']} {reference['core_version']}" ]
formats = [ "{{:<{}}}", "{{:<{}}}", "{{:<{}}}", "{{:^{}}}", "{{:^{}}}", "{{:>{}}}", "{{:<{}}}" ]
data_lines = []
col_widths = [ len(header) for header in headers ]

name_regexp = re.compile(r'(libraries|examples)/([^/]+)/(examples/|extras/)?(.*)')

# pair every current report with its reference, by FQBN
reports = []
for report_file in glob.glob("arduino-*.json"):
    with open(report_file, 'r') as f:
        new_report_data = json.load(f)
    fqbn = new_report_data.get('boards', [{}])[0].get('board')
    old_board_report = old_reports.get(fqbn)
    if not old_board_report:
        # no current results, or no reference for this FQBN
        continue
    package, board, opts = fqbn.split(':')[1:4]
    reports.append(( package, board, opts, report_file, new_report_data, { 'boards': [ old_board_report ] } ))

os.makedirs(output_folder, exist_ok=True)

# calculate deltas and write output files
for package, board, opts, report_file, new_report_data, old_report_data in sorted(reports, key=lambda r: r[:3]):

    # the output file will be a copy of the new data, plus some fields
    output_report_data = copy.deepcopy(new_report_data)
    sketch_now_missing = 0
    sketch_was_missing = 0
    updated_sketches = 0
    finals = defaultdict(dict)

    output_sketches = output_report_data['boards'][0]['sketches']

    group_lines = []

    for sketch in sorted(output_sketches, key=lambda s: s['name']):
        match = name_regexp.search(sketch['name'])
        display_name = f"{match.group(2)} {match.group(4)}" if match else sketch['name']

        sketch_ok = sketch['compilation_success']
        old_sketch = next((s for s in old_report_data['boards'][0]['sketches'] if s['name'] == sketch['name']), None)
        old_sketch_ok = old_sketch and old_sketch['compilation_success']

        if not sketch_ok:
            # compile time issue in the new data, skip
            if old_sketch_ok:
                group_lines.append(( display_name, "-- compile failed" ))
                sketch_now_missing += 1
            continue
        if not old_sketch_ok:
            # compile time issue or missing old data, skip
            group_lines.append(( display_name, "-- old data missing" ))
            sketch_was_missing += 1
            continue
        deltas = {}
        for entry in sketch['sizes']: # list, name is "flash" or "RAM for global variables"
            key = entry['name']
            old_match = next((e for e in old_sketch['sizes'] if e['name'] == entry['name']), None)
            if not old_match:
                # major group missing in old data, skip
                group_lines.append(( display_name, f"-- old group mismatch" ))
                continue
            # add "previous" data from the old report
            entry['previous'] = old_match['current']
            curr_abs = entry['current']['absolute']
            prev_abs = entry['previous']['absolute']
            if isinstance(curr_abs, str) or isinstance(prev_abs, str):
                # "N/A", ignore delta for this entry
                continue
            deltas[key] = entry['delta'] = {
                'absolute': curr_abs - prev_abs,
                'relative': ((curr_abs - prev_abs) * 100 // prev_abs) / 100 if prev_abs > 0 else "N/A"
            }
            update_final_deltas(finals[key], entry['maximum'], entry['delta'])

        # update display name in output file
        sketch['name'] = display_name

        if not deltas:
            group_lines.append(( display_name, "-- no matches" ))
        else:
            updated_sketches += 1
            ram_delta = deltas["RAM for global variables"]['absolute'] if "RAM for global variables" in deltas else "N/A"
            flash_delta = deltas["flash"]['absolute'] if "flash" in deltas else "N/A"
            group_lines.append(( display_name, f"{flash_delta:6} {ram_delta:6}" ))

    if group_lines:
        print(f"::group::{package} {board} {opts}")
        max_name_len = max(len(display_name) for display_name, _ in group_lines)
        for display_name, text in group_lines:
           print(f"{package} {board} {opts} {display_name:{max_name_len}} {text}")
        print(f"::endgroup::")

    # update the board-specific 'sizes' list with the new deltas
    output_report_data['boards'][0]['sizes'] = []
    for entry_name, final_values in finals.items():
        output_report_data['boards'][0]['sizes'].append({
            "name": entry_name,
            **final_values
        })

    # write new data + valid deltas
    with open(os.path.join(output_folder, report_file), 'w') as f:
        json.dump(output_report_data, f, indent=2)

    # generate a line for the summary table
    changes = f"{sketch_now_missing} lost" if sketch_now_missing else ""
    changes += ", " if sketch_now_missing and sketch_was_missing else ""
    changes += f"{sketch_was_missing} new" if sketch_was_missing else ""
    data_line = [ package, board, opts,
                  range_str(finals["flash"].get('delta')),
                  range_str(finals["RAM for global variables"].get('delta')),
                  updated_sketches or '-',
                  changes ]

    col_widths = [ max(len(str(data_line[i])), col_widths[i]) for i in range(len(data_line)) ]
    data_lines.append(data_line)

# format and output table
format_string = "| " + " | ".join([ formats[i].format(col_widths[i]) for i in range(len(col_widths)) ]) + " |"
spacer_string = "+-" + "-+-".join([ "-"*col_widths[i] for i in range(len(col_widths)) ]) + "-+"

print(spacer_string)
print(format_string.format(*headers))

last_package = None
for data_line in data_lines:
    if data_line[0] != last_package:
        last_package = data_line[0]
        print(spacer_string)
    else:
        data_line[0] = ""
    print(format_string.format(*data_line))

print(spacer_string)
