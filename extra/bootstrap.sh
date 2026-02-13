#!/bin/bash

# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# Initialize the Zephyr workspace from a cleanly cloned ArduinoCore-zephyr
# repository, fetching only the necessary modules and blobs for the supported
# boards.

. $(dirname $0)/functions

if [ ! -f platform.txt ]; then
  echo Launch this script from the root core folder as ./extra/bootstrap.sh
  exit 2
fi

NEEDED_HALS=$(get_unique_values_from_text_file boards.txt 'build.zephyr_hals')
NEEDED_TOOLCHAINS=$(get_unique_values_from_text_file boards.txt 'build.zephyr_toolchain')

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
west packages pip --install
log_msg "endgroup"

log_msg "group" "Installing Zephyr SDK 0.16.8: $NEEDED_TOOLCHAINS"
west sdk install --version 0.16.8 -t $NEEDED_TOOLCHAINS
log_msg "endgroup"

NEEDED_HALS="arduino-api $NEEDED_HALS"
log_msg "group" "Fetching blobs for: $NEEDED_HALS"
west blobs fetch $NEEDED_HALS
log_msg "endgroup"
