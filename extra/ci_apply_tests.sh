#!/bin/bash

# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# This script builds the per-board test list for GitHub Actions CI.
# It consumes the pre-downloaded archives in test-data/ (produced by
# ci_fetch_tests.sh) and populates ALL_TESTS and ALL_LIBRARIES in
# $GITHUB_ENV for the current board variant.
#
# The core under test must be extracted in the 'ArduinoCore-zephyr'
# subdirectory, and test-data/ must be present in the working directory.

set -e

if [ "$#" -lt 2 ]; then
	echo "Usage: $0 <artifact> <variant>"
	exit 1
fi

if [ -z "$GITHUB_ENV" ] || [ ! -d ArduinoCore-zephyr/ ] || [ ! -d test-data/ ]; then
	echo "Not in a Github CI run or missing prerequisites (ArduinoCore-zephyr/, test-data/)."
	exit 1
fi

ARTIFACT=$1
VARIANT="$2"
VARIANT_DIR="ArduinoCore-zephyr/variants/${VARIANT}"

ALL_TESTS=$(mktemp)

get_repo_key() {
	# $1: type of fetch
	# $2: repo (owner/name)
	echo "${1}__${2//\//__}"
}

search_for_sketches_in() {
	local folder="$1"
	find "$folder" -name "*.ino" 2>/dev/null | sed -e 's/^\.\///'
}

extract_and_search() {
	# $1: archive path
	# $2: inner folder glob pattern (e.g. "*-project-*" or "project-branch")
	# $3: output folder (destination after extraction)
	# $4+: sub-paths to search within the output folder (empty = whole folder)
	local archive="$1"
	local inner_pattern="$2"
	local output_folder="$3"
	shift 3

	if [ ! -d "${output_folder}" ]; then
		local temp_dir
		temp_dir=$(mktemp -d)
		tar -xzf "$archive" -C "$temp_dir"
		local inner_folder
		inner_folder=$(ls -d "${temp_dir}/"${inner_pattern} 2>/dev/null | head -1)

		mkdir -p "$(dirname "$output_folder")"
		mv "$inner_folder" "$output_folder"
		rm -rf "$temp_dir"
	fi

	if [ $# -eq 0 ]; then
		search_for_sketches_in "$output_folder" >> "$ALL_TESTS"
	else
		for item in "$@"; do
			search_for_sketches_in "$output_folder/${item}" >> "$ALL_TESTS"
		done
	fi
}

get_latest_release() {
	local folder="$1"
	local repo="$2"
	local project="${repo##*/}"
	local key="$(get_repo_key release "$repo")"
	shift 2

	echo "Extracting latest release of ${repo}"
	extract_and_search "test-data/${key}.tar.gz" "*-${project}-*" \
		"ArduinoCore-zephyr/${folder}/${project}" "$@"
}

get_branch_tip() {
	local folder="$1"
	local repo="$2"
	local branch="$3"
	local project="${repo##*/}"
	local key="$(get_repo_key "branch_$branch" "$repo")"
	shift 3

	echo "Extracting branch ${branch} of ${repo}"
	extract_and_search "test-data/${key}.tar.gz" "${project}-${branch}" \
		"ArduinoCore-zephyr/${folder}/${project}" "$@"
}

# Collect built-in tests from the core
search_for_sketches_in ArduinoCore-zephyr/libraries/ >> "$ALL_TESTS"
search_for_sketches_in ArduinoCore-zephyr/examples/ >> "$ALL_TESTS"

# Source common and artifact-specific setups to extract external repos and
# add their examples, then apply the variant-specific setup to filter results
[ -f extra/artifacts/_common.test_setup.sh ] && \
	. extra/artifacts/_common.test_setup.sh
[ -f "extra/artifacts/${ARTIFACT}.test_setup.sh" ] && \
	. "extra/artifacts/${ARTIFACT}.test_setup.sh"

echo "ALL_LIBRARIES<<EOF" >> "$GITHUB_ENV"
find ArduinoCore-zephyr/libraries/ -name library.properties | while read -r propfile; do
	# Version constraints are ignored as they are not supported by compile-sketches
	grep '^depends=' "$propfile" | cut -d= -f2- | tr ',' '\n' | \
		sed -e 's/\s*(.*)\s*$//' | while read -r dep; do
		[ -z "$dep" ] || printf " - name: \"%s\"\n" "$dep" >> "$GITHUB_ENV"
	done
done
echo "EOF" >> "$GITHUB_ENV"

if [ -f $VARIANT_DIR/skip_these_examples.txt ] ; then
	cat $VARIANT_DIR/skip_these_examples.txt | sed -e 's/\s*#.*//' -e '/^\s*$/d' | while read -r pattern; do
		sed -i -e "\\|^\\(ArduinoCore-zephyr/\\)\\?${pattern}|d" "$ALL_TESTS"
	done
fi

# output the collected test list for this variant to both the console and
# the GITHUB_ENV file
echo -e "\nCollected tests for ${VARIANT}:"
echo "ALL_TESTS<<EOF" >> "$GITHUB_ENV"
while read -r infile; do
	printf " - \"%s\"\n" "$(dirname "$infile")"
done < "$ALL_TESTS" | sort | tee -a "$GITHUB_ENV"
echo "EOF" >> "$GITHUB_ENV"
