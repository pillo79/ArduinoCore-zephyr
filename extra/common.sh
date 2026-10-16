# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# Shared helpers for the scripts in extra/. Source this file, do not run it.

# Usage: log_msg <group|endgroup|notice|warning|error> [message]
#
# In GitHub Actions, emits the message as a workflow command so it is rendered
# as a collapsible group or an annotation. Elsewhere, prints plain text.
log_msg() {
	if [ -n "${GITHUB_WORKSPACE:-}" ] ; then
		echo "::$1::${2:-}"
		return
	fi

	case "$1" in
		group)    echo " - ${2:-}" ;;
		endgroup) ;;
		*)        echo "$1: ${2:-}" ;;
	esac
}
