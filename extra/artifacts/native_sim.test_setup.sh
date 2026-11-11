# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# This script is sourced from extra/ci_apply_tests.sh, after the common
# setup, to provide the native_sim tests.
#
# native_sim is not a real board: it tests the sketches of all the other
# cores and boards. Add the tests of each core and variant setup, without
# the filters they apply for their own boards (native_sim filters its own
# sketches in its variant setup and known issues).

eval "native_sim_skip_for_this_board() $(declare -f skip_for_this_board | tail -n +2)"
skip_for_this_board() { :; }

for other_setup in extra/artifacts/*.test_setup.sh variants/*/test_setup.sh ; do
	case "$other_setup" in
		*/_common.test_setup.sh|*/native_sim.test_setup.sh|variants/native_sim_*) continue ;;
	esac
	. "$other_setup"
done

# (repositories listed by several setups add the same sketches; there is no
# test list when sourced by ci_fetch_tests.sh)
[ -z "${ALL_TESTS:-}" ] || sort -u -o "$ALL_TESTS" "$ALL_TESTS"

eval "skip_for_this_board() $(declare -f native_sim_skip_for_this_board | tail -n +2)"
unset -f native_sim_skip_for_this_board
