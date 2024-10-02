#!/bin/bash

if [ ! -f platform.txt ]; then
  echo Launch this script from the root core folder as ./extras/package.sh VERSION
  exit 2
fi

VERSION=$1

tar  --exclude=extras/** --exclude=.git* --exclude=build --exclude=venv --exclude=samples -cjhf ../arduino-core-zephyr-llext-${VERSION}.tar.bz2 .