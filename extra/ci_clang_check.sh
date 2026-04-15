#!/usr/bin/env bash

# Copyright ARDUINO SRL
# SPDX-License-Identifier: Apache-2.0

# parse arguments
while getopts "p:f:o:r:e:i:" opt; do
	case $opt in
		p) CHECK_PATH="$OPTARG" ;;
		f) CHECK_FILES_FROM="$OPTARG" ;;
		e) EXCLUDE_REGEX="$OPTARG" ;;
		i) INCLUDE_REGEX="$OPTARG" ;;
		*) echo "Invalid option: -$OPTARG" >&2 ; exit 1 ;;
	esac
done

if [[ -z "$CHECK_FILES_FROM" ]] && [[ -z "$CHECK_PATH" ]]; then
	echo "No source input provided. Fallback to all files." >&2
	CHECK_PATH="."
elif [[ -f "$CHECK_FILES_FROM" ]]; then
	echo "Checking files listed in 'check-files-from'." >&2
elif [[ ! -z "$CHECK_PATH" ]] && [[ -d "$CHECK_PATH" ]]; then
	echo "Checking directory specified by 'check-path'." >&2
else
	echo "::warning::Invalid inputs provided. Fallback to all files." >&2
	CHECK_FILES_FROM=""
	CHECK_PATH="."
fi

# Set the regex to an empty string regex if nothing was provided
if [[ -z $EXCLUDE_REGEX ]]; then
	EXCLUDE_REGEX="^$"
fi

# Set the filetype regex if nothing was provided.
# Find all C/C++/Protobuf/CUDA files:
#   h, H, hpp, hh, h++, hxx
#   c, C, cpp, cc, c++, cxx
#   ino, pde
#   proto
#   cu
if [[ -z $INCLUDE_REGEX ]]; then
	INCLUDE_REGEX='^.*\.((((c|C)(c|pp|xx|\+\+)?$)|((h|H)h?(pp|xx|\+\+)?$))|(ino|pde|proto|cu))$'
fi

cd "$GITHUB_WORKSPACE" || exit 2

if [[ -f "$CHECK_FILES_FROM" ]]; then
	# Use the provided list of files to check.
	src_files=$(grep -E "$INCLUDE_REGEX" "$CHECK_FILES_FROM")
else
	# Find all source files in the provided path, excluding .git directories.
	src_files=$(find "$CHECK_PATH" -name .git -prune -o -regextype posix-egrep -regex "$INCLUDE_REGEX" -print)
fi

exit_code=0
IFS=$'\n' # Loop below should separate on new lines, not spaces.
for file in $src_files; do
	# Only check formatting if the path doesn't match the regex
	[[ ${file} =~ $EXCLUDE_REGEX ]] && continue

	clang-format -i -style=file "${file}" 2>&1
	changes=$(git diff -U0 --color=always ${file})
	[ -z "$changes" ] && continue

	exit_code=1
	echo "$changes" | tail -n +5 | while IFS= read -r line ; do
		if [[ $line =~ @@\ -([0-9]+),?([0-9]*)\ \+([0-9]+),?([0-9]*)\ @@ ]]; then
			# Extract the line numbers from the diff output
			git_start_line=${BASH_REMATCH[1]}
			git_line_count=${BASH_REMATCH[2]:-1}
			# fixed_start_line=${BASH_REMATCH[3]}
			# fixed_line_count=${BASH_REMATCH[4]:-1}

			git_end_line=$((git_start_line + git_line_count - 1))

			echo "---"
			echo "::error file=${file},line=${git_start_line},endLine=${git_end_line},title=Fix this formatting::${file}, lines ${git_start_line}-${git_end_line}:"
		else
			# diff line, print it as is (with color)
			echo "$line"
		fi
	done
done

[ "$exit_code" -ne 0 ] && echo "---"

exit $exit_code
