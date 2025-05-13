#!/bin/bash

if [ ! -f platform.txt ]; then
  echo Launch this script from the root core folder as ./extra/bootstrap.sh
  exit 2
fi

python3 -m venv venv
source venv/bin/activate
pip install west
west init -l .
west update "$@"
west zephyr-export
pip install -r ../zephyr/scripts/requirements-base.txt
west sdk install --version 0.17.0 -t arm-zephyr-eabi

# add here the required blobs based on supported platforms
west blobs fetch hal_nxp
