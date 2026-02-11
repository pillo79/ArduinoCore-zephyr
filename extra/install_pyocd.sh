#!/bin/bash

# Copyright (c) 2024 Arduino SA
# SPDX-License-Identifier: Apache-2.0

python3 -m pip install pyocd
# add install dir to PATH
# echo /Users/$USER/Library/Python/3.9/bin > /etc/paths.d/pyocd
pyocd pack update
pyocd pack install R7FA8D1AH
pyocd pack install mcxn947
