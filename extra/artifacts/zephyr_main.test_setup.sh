# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# This script is sourced by ci_fetch_tests.sh / ci_apply_tests.sh to provide
# artifact-specific tests for Zephyr CI tests.
#
# Two helper functions are available:
# - get_branch_tip <folder> <repo> <branch> [<path> ...]
# - get_latest_release <folder> <repo> [<path> ...]
#
# Board-specific repos are declared in each variant's test_setup.sh instead.

# ArduinoBLE
get_branch_tip libraries arduino-libraries/ArduinoBLE master \
	examples/Central/LedControl \
	examples/Central/Scan \
	examples/Peripheral/Advertising/EnhancedAdvertising \
	examples/Peripheral/ButtonLED \

# Arduino_SecureElement
get_latest_release libraries arduino-libraries/Arduino_SecureElement \
