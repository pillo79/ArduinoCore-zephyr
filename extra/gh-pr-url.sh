#!/bin/bash
# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# Given a PR number, print the api.github.com link to the artifact produced by
# the "package-index-json" step on the last "Package, test and upload core" run
# for that PR.
#
# Designed to be installed in /usr/local/bin and be used as:
#
#   gh pr-url <pr-number> [repo]

set -euo pipefail

if [ $# -lt 1 ]; then
	echo "Usage: $0 <pr-number> [repo]" >&2
	exit 1
fi

PR_NUM="$1"
REPO="${2:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"

PR_TAG="${REPO}#${PR_NUM}"

BRANCH="$(gh pr view "${PR_NUM}" --json headRefName -q .headRefName)"
RUN_ID="$(gh run list \
	  --workflow package_core.yml \
	  --branch "${BRANCH}" \
	  --limit 1 \
	  --json databaseId -q '.[0].databaseId')"

if [ -z "${RUN_ID}" ]; then
	echo "No CI run found for ${PR_TAG} (branch ${BRANCH})" >&2
	exit 1
fi

ARTIFACT_NAME="package_arduino_zephyr_pr_${PR_NUM}_ci_index.json"

ARTIFACT_ID="$(gh api "/repos/${REPO}/actions/runs/${RUN_ID}/artifacts" \
	       -q ".artifacts[] | select(.name == \"${ARTIFACT_NAME}\") | .id")"

if [ -z "${ARTIFACT_ID}" ]; then
	echo "No package index found for ${PR_TAG} (CI run ${RUN_ID})"
	exit 1
fi

echo "https://api.github.com/repos/${REPO}/actions/artifacts/${ARTIFACT_ID}/zip#${ARTIFACT_NAME}"
