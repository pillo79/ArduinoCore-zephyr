#!/usr/bin/env python3

# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# Script to analyze CI test logs, download previously generated size reports,
# and calculate size deltas in the official JSON report format.
#
# This scripts expects the following arguments:
#  - <prev_sha>: SHA of the base report to get, used for delta calculation
#  - <reports_folder>: directory to populate with the delta reports
#
# The script performs the following actions:
# - downloads the previous report archive from AWS
# - extracts it in the output folder
# - for each JSON report file in the output folder:
#   - calculates the delta with the corresponding report in the
#     current directory (if it exists and both reports are valid)
#   - updates the output report file with the delta information.

from collections import defaultdict
import copy
import json
import os
import requests
import re
import sys
import tarfile

def extract_url(url, local_path):
    archive_path = local_path + "/file.tar.bz2"
    try:
        os.makedirs(local_path, exist_ok=True)
        response = requests.get(url)
        response.raise_for_status()
        with open(archive_path, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded {url} to {local_path}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        raise

    try:
        with tarfile.open(archive_path, 'r:bz2') as tar:
            tar.extractall(path=local_path)
        print(f"Extracted {archive_path} to {local_path}")
    except Exception as e:
        print(f"Error extracting {archive_path}: {e}")
        raise

if not len(sys.argv) == 3:
    print("Usage: ci_calc_size_reports.py <prev_sha> <output_folder>")
    sys.exit(1)

prev_sha = sys.argv[1]
output_folder = sys.argv[2]

# get the previous data to the output folder
extract_url(f"https://downloads.arduino.cc/cores/zephyr/size-reports/size-reports-{prev_sha[:7]}.tar.bz2", output_folder)

# loop every JSON file in the output folder
for dirent in os.scandir(output_folder):
    if dirent.is_file() and dirent.name.endswith(".json"):
        with open(dirent.path, 'r') as f:
            old_report_data = json.load(f)
        # test if the current file exists
        if not os.path.exists(dirent.name):
            # no: remove the old report to prevent confusion
            os.remove(dirent.path)
            continue
        with open(dirent.name, 'r') as f:
            new_report_data = json.load(f)

        # the output file will be a copy of the new data, plus some fields
        output_report_data = copy.deepcopy(new_report_data)
        for sketch in output_report_data['boards'][0]['sketches']:
            if not sketch['compilation_success']:
                # compile time issue in the new data, skip
                continue
            old_sketch = next((s for s in old_report_data['boards'][0]['sketches'] if s['name'] == sketch['name']), None)
            if not old_sketch or not old_sketch['compilation_success']:
                # compile time issue or missing old data, skip
                continue
            for entry in sketch['sizes']:
                old_match = next((e for e in old_sketch['sizes'] if e['name'] == entry['name']), None)
                if not old_match:
                    # major group missing in old data, skip
                    continue
                # add "previous" data from the old report 
                entry['previous'] = old_match['current']
                curr_abs = entry['current']['absolute']
                prev_abs = entry['previous']['absolute']
                if isinstance(curr_abs, str) or isinstance(prev_abs, str):
                    # "N/A", ignore delta for this entry
                    continue
                entry['delta'] = { 
                    'absolute': curr_abs - prev_abs,
                    'relative': (curr_abs - prev_abs) / prev_abs if prev_abs > 0 else None
                }

        # overwite old file with new data + valid deltas
        with open(dirent.path, 'w') as f:
            json.dump(output_report_data, f, indent=2)
