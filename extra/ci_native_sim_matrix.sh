#!/bin/bash

# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# This script splits the native_sim tests in groups, one per test job.
# The groups are the ones of the CI report (see TestEntry in ci_shared.py):
# the name after 'libraries/' or 'examples/' in the sketch path. The loader
# tests group is not in the test list, and is always present.
#
# Usage:
#   ci_native_sim_matrix.sh <tests.txt>
#     print the test matrix as a compact JSON array of { group, id }, where
#     id is the job marker id of the test job
#   ci_native_sim_matrix.sh -g <group> <tests.txt>
#     print the sketch directories of that group, one per line
#
# <tests.txt> is the list written by ci_apply_tests.sh.

set -e

GROUP=
if [ "$1" == "-g" ]; then
	GROUP=$2
	shift 2
fi

if [ "$#" -ne 1 ]; then
	echo "Usage: $0 [-g <group>] <tests.txt>" >&2
	exit 1
fi

# "<group> <sketch dir>" lines, as for the report
groups() {
	sed -n -E 's#^((ArduinoCore-zephyr/)?(libraries|examples)/([^/]+)/.*)$#\4 \1#p' "$1"
}

if [ -n "$GROUP" ]; then
	groups "$1" | awk -v g="$GROUP" '$1 == g && !seen[$0]++ { sub(/^[^ ]* /, ""); print }'
else
	{ echo loader; groups "$1" | cut -d' ' -f1; } |
		LC_ALL=C sort -u | jq -R -c -s 'split("\n") | map(select(length > 0) | { group: ., id: "test-native_sim-\(.)" })'
fi
