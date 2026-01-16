#!/bin/bash

# This script generates a SemVer-compatible version number based on Git tags.
#
# If the current commit is tagged, it returns that version. If not, it
# generates a version string based on the next patch number and the current
# commit hash.
#
# If the tag is a simple "<maj>.<min>.<patch>", git describe will output:
#
#     <maj>.<min>.<patch>-<number-of-commits-since-tag>-g<commit-hash-dirty>
#
# The regexp splits the patch number, awk converts the tokens to:
#
#     <maj>.<min>.<next-patch>-0.dev+<commit-hash-dirty>
#
# If the tag refers to a pre-release, like "<maj>.<min>.<patch>-<extra-stuff>",
# sed will output a total of 4 arguments and the format of the final awk output
# will be:
#
#     <maj>.<min>.<patch>-<extra-stuff>-0.dev+<commit-hash-dirty>
#
# These are among the lowest possible SemVer versions greater than the last
# tagged version.
#
# If there are no tags at all (for example when run in a fork etc), it defaults
# to "9.9.9-<date>+<commit-hash-dirty>".

# In CI, BRANCH_NAME points to the branch or tag ref that triggered the
# workflow run (e.g., "refs/heads/main" or "refs/tags/v1.2.3"). Without this,
# git describe would use HEAD, which is a temporary detachead commit.
# If BRANCH_NAME is not set, assume a local clone. Fall back to using HEAD
# and also include --dirty to test for uncommitted changes.

GIT_TARGET=${BRANCH_NAME:---dirty HEAD}

VERSION=$(git describe --tags --exact-match $GIT_TARGET 2>/dev/null)
if [ -z "$VERSION" ]; then
	VERSION=$(git describe --tags $GIT_TARGET 2>/dev/null |
		#         (1.............) (2...)*
		sed 's/\.\([[:digit:]]\+\)\(-.*\)*-[[:digit:]]\+-g/ \1 \2 /' |
		awk '{ if (NF==3) { print $1 "." ($2+1) "-0.dev+" $3 } else { print $1 "." $2 $3 "-0.dev+" $4 }}')
	if [ -z "$VERSION" ]; then
		VERSION="9.9.9-$(date '+%Y%m%d-%H%M%S')+$(git describe --always $GIT_TARGET)"
	fi
fi
echo $VERSION
