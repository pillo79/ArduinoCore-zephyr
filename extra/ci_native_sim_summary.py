#!/usr/bin/env python3

# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# Script to write a short markdown summary of the native_sim test jobs.
#
# Each failed test job of the native_sim matrix (see ci_native_sim_matrix.sh)
# is listed with a link to its log and the count of its sketches in each
# category (see CATEGORIES), followed by the totals of all the jobs. The
# reports are evaluated against the known issues with the same rules used for
# the CI summary (see ci_collect_data.py): a job fails on unexpected results
# only, and the known issues that do not build are counted apart. The job of
# a board native_sim poses as also uses the known issues of that board.
#
# This script expects the following inputs:
#
#  - Environment variables:
#     - NATIVE_SIM_MATRIX: native_sim test jobs, see ci_native_sim_matrix.sh
#
#  - Files in the current directory:
#     - native_sim-sketches-<group>.json: the report of each test job
#     - prereqs/<id>.json: job completion markers, with job status and log link
#     - variants/*/known_example_issues*.txt: expected errors
#
# Usage: ci_native_sim_summary.py
#  The summary is written to stdout. Exits with an error if any job failed.

import json
import os
import sys

from ci_shared import (
    load_known_issues, load_sketch_reports, evaluate_test,
    RAN_ICON, RUN_FAILED_ICON,
)

VARIANT = "native_sim_native_64"

# sketch categories, in display order, with their icon and text
CATEGORIES = {
    'build_failed': (":red_circle:", "build failed"),   # unexpected compile error
    'not_built': (":no_entry_sign:", "not built"),      # known issue
    'unavailable': (":heavy_minus_sign:", "not available"),     # not built, not in the package
    'only_built': (":green_circle:", "only built"),     # no expect logic
    'ran': (RAN_ICON, "ran"),                            # all run checks passed
    'ran_failing': (RUN_FAILED_ICON, "ran failing"),     # some run checks failed
}

def category(report, excepted):
    """
    Returns the category of a sketch report.
    """
    if report.get('available') is False:
        return 'unavailable'
    if not report.get('compilation_success', False):
        return 'not_built' if excepted else 'build_failed'
    run_success = report.get('run_success')
    if run_success is None:
        return 'only_built'
    return 'ran' if run_success else 'ran_failing'

def format_counts(counts):
    """
    Returns the non-zero category counts, as icons and text.
    """
    return ", ".join(f"{icon} {counts[cat]} {text}" for cat, (icon, text) in CATEGORIES.items() if counts[cat])

matrix = json.loads(os.environ.get('NATIVE_SIM_MATRIX') or '[]')

lines = []
totals = { cat: 0 for cat in CATEGORIES }
total_tests = 0
all_passed = bool(matrix)
for job in matrix:
    group, job_id = job['group'], job['id']

    marker = {}
    try:
        with open(f"prereqs/{job_id}.json", 'r') as f:
            marker = json.load(f)
    except (OSError, ValueError):
        pass
    name = f"[`{group}`]({marker['job_url']})" if marker.get('job_url') else f"`{group}`"

    # (the job of a board native_sim poses as has its variant)
    mimic = (group, job['variant']) if job.get('variant') else None
    exceptions, warning_filters = load_known_issues(VARIANT, mimic)
    reports, error = load_sketch_reports(f"native_sim-sketches-{group}.json")
    # (a job that wrote its report completed its tests, even if it failed)
    if error:
        all_passed = False
        lines.append(f":x: {name}: tests did not complete")
        continue

    failed = False
    counts = { cat: 0 for cat in CATEGORIES }
    for report in reports:
        test = evaluate_test(report, exceptions, warning_filters)
        failed = failed or not test.status.passed
        counts[category(report, test.excepted)] += 1
    for cat in CATEGORIES:
        totals[cat] += counts[cat]
    total_tests += len(reports)

    # passing jobs are only counted in the totals
    if failed:
        all_passed = False
        lines.append(f":x: {name}: {format_counts(counts)}")

lines.append(f"**{total_tests} tests**: {format_counts(totals)}")

print(f"### native_sim tests {'PASSED :green_circle:' if all_passed else 'FAILED :red_circle:'}\n")
for line in lines:
    print(f"- {line}")

sys.exit(0 if all_passed else 1)
