#!/bin/bash

FORCE=false

while getopts "hfl" opt; do
	case $opt in
		h)
			echo "Usage: $0 [-hfl]"
			echo "  -h  Show this help message"
			echo "  -f  Force build all targets"
			exit 0
			;;
		f)
			FORCE=true
			;;
		*)
			echo "Invalid option: -$OPTARG" >&2
			exit 1
			;;
	esac
done

jq -cr '.[]' < ./extra/targets.json | while read -r item; do
	board=$(jq -cr '.board // ""' <<< "$item")
	args=$(jq -cr '.args // ""' <<< "$item")

	variant=$(extra/get_variant_name.sh "$board" || echo "$board")
	echo && echo
	echo ${variant}
	echo ${variant} | sed -e 's/./=/g'

	./extra/build.sh "$board" $args
	result=$?

	echo
	echo "${variant} result: $result"
	[ $result -ne 0 ] && ! $FORCE && exit $result
done

exit 0
