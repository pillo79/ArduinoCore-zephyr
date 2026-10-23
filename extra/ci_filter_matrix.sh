#!/bin/bash

# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# This script filters a CI job matrix, keeping only the entries whose
# prerequisites were successfully completed.
#
# Each entry of the input matrix lists the ids of the jobs it depends on in
# its 'requires' field (see ci_get_build_info.sh). Each job publishes its
# outcome as a 'prereq-<id>' artifact containing a <id>.json marker file:
#
#   {
#     "id": "<id>",
#     "status": "success" | "failure",
#     "job_url": "<URL of the job log>"
#   }
#
# The markers are collected in <ids_dir> before running this script. They are
# also used by ci_collect_data.py to link each job log in the CI summary.
#
# The filtered matrix is printed to stdout as compact JSON. A warning is
# emitted for each entry that is removed.
#
# Usage: ci_filter_matrix.sh <ids_dir> <matrix_json>

set -e

if [ $# -ne 2 ]; then
	echo "Usage: $0 <ids_dir> <matrix_json>"
	exit 1
fi

IDS_DIR=$1
MATRIX=$2

# ids of the jobs that completed successfully
AVAILABLE=$(cat "$IDS_DIR"/*.json 2>/dev/null | jq -cs 'map(select(.status == "success") | .id)')

jq -r --argjson available "$AVAILABLE" '
	.[] | (.requires - $available) as $missing | select($missing | length > 0)
	| "::warning::Skipping \(.board // .artifact)\(if .link_mode then ":\(.link_mode)" else "" end): missing \($missing | join(", "))"
' <<< "$MATRIX" >&2

jq -c --argjson available "$AVAILABLE" 'map(select(.requires - $available | length == 0))' <<< "$MATRIX"
