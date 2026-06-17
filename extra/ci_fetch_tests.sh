#!/bin/bash

# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# This script downloads all external test repositories referenced by all
# test_setup.sh files (artifact-level and variant-level). Each repo is
# downloaded as a complete archive into the test-data/ directory.
#
# The downloaded archives are later consumed by ci_apply_tests.sh, which
# extracts only the paths relevant for a specific board variant.
#
# This script is intended to run once per workflow, before the per-board
# test jobs. Run from the repository root (needs extra/ and variants/).

set -e

if [ ! -d extra/artifacts/ ]; then
	echo "Must be run from the ArduinoCore-zephyr root directory."
	exit 1
fi

DOWNLOAD_DIR="test-data"
mkdir -p "$DOWNLOAD_DIR"

get_repo_key() {
	# $1: type of fetch
	# $2: repo (owner/name)
	echo "${1}__${2//\//__}"
}

get_latest_release() {
	# $1: folder (ignored at fetch time)
	# $2: repo (owner/name)
	# $3+: paths (ignored at fetch time)
	local repo="$2"
	local key="$(get_repo_key release "$repo")"

	local file="${DOWNLOAD_DIR}/${key}.tar.gz"
	[ -f "${file}" ] && return # already downloaded

	local url=$(curl -s "https://api.github.com/repos/${repo}/releases/latest" | jq -r '.tarball_url')
	[ $url == "null" ] && echo "::error::No releases found for ${repo}" 2>&1 && exit 1

	echo "::group::Downloading latest release of ${repo}"
	wget -nv "$url" -O "${file}"
	echo "::endgroup::"
}

get_branch_tip() {
	# $1: folder (ignored at fetch time)
	# $2: repo (owner/name)
	# $3: branch
	# $4+: paths (ignored at fetch time)
	local repo="$2"
	local branch="$3"
	local key="$(get_repo_key "branch_$branch" "$repo")"

	local file="${DOWNLOAD_DIR}/${key}.tar.gz"
	[ -f "${file}" ] && return # already downloaded

	local url="https://github.com/${repo}/archive/refs/heads/${branch}.tar.gz"

	echo "::group::Downloading branch ${branch} of ${repo}"
	wget -nv "$url" -O "${file}"
	echo "::endgroup::"
}

# Source all test_setup.sh files to pick up any package references
# (order doesn't matter since we only gather files at fetch time)

for artifact_setup in extra/artifacts/*.test_setup.sh; do
	. "$artifact_setup"
done
