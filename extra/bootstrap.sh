#!/bin/bash
#
# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

set -e

log_msg() {
	if [ -n "$GITHUB_WORKSPACE" ] ; then
		echo "::$1::$2"
	else
		echo " - $2"
	fi
}

if [ ! -f platform.txt ]; then
  echo Launch this script from the root core folder as ./extra/bootstrap.sh
  exit 2
fi

get_unique_field_values() {
  local field="$1"
  local file="$2"
  grep "$field=" $file | cut -d '=' -f 2 | xargs -n 1 echo | sort -u | xargs echo
}

NEEDED_HALS=$(get_unique_field_values 'build.zephyr_hals' boards.txt)
NEEDED_TOOLCHAINS=$(get_unique_field_values 'build.zephyr_toolchain' boards.txt)

HAL_FILTER="-hal_.*"
for hal in $NEEDED_HALS; do
  HAL_FILTER="$HAL_FILTER,+$hal"
done

log_msg "group" "Bootstrapping Python environment for Zephyr"
python3 -m venv venv
source venv/bin/activate
pip install west protobuf grpcio-tools
log_msg "endgroup"

log_msg "group" "Initializing Zephyr workspace and modules: $HAL_FILTER"
west init -l .
west config manifest.project-filter -- "$HAL_FILTER"
west update "$@"
west zephyr-export
pip install -r ../zephyr/scripts/requirements-base.txt
log_msg "endgroup"

TOOLCHAIN_VERSIONS=$(for tc in $NEEDED_TOOLCHAINS; do
  version=$(jq -r --arg name "$tc" '.toolsDependencies[] | select(.name == $name) | .version' extra/artifacts/_common.json)
  echo "$version $tc"
done | sort -V)

for version in $(echo "$TOOLCHAIN_VERSIONS" | cut -d ' ' -f 1 | sort -u -V); do
  toolchains=$(echo "$TOOLCHAIN_VERSIONS" | awk -v v="$version" '$1 == v { print $2 }')
  log_msg "group" "Installing Zephyr SDK ${version}: ${toolchains}"
  west sdk install --version "$version" -t $toolchains
  log_msg "endgroup"
done

NEEDED_HALS="arduino-api $NEEDED_HALS"
log_msg "group" "Fetching blobs for: $NEEDED_HALS"
west blobs fetch $NEEDED_HALS
log_msg "endgroup"
