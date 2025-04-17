#!/bin/bash

set -e

TOOL_NAME=$(basename $1)
VERSION=$2

BASE_DIR=$(readlink -f $(dirname $0)/..)
TOOL_DIR="$BASE_DIR/extra/$TOOL_NAME"
if ! [ -d "$TOOL_DIR" ] || [ -z "$VERSION" ] ; then
	echo "Usage: $0 <tool_name> <version>"
	exit 1
fi

DIR=${BASE_DIR}/distrib

hash_file() {
	plat=$1
	file=$2
	name=$(basename $file)
	hash=$(sha256sum $file | cut -d ' ' -f 1)
	len=$(stat -c %s $file)
	cat << EOF
{
  "host": "$plat",
  "url": "https://downloads.arduino.cc/tools/$name",
  "archiveFileName": "$name",
  "checksum": "SHA-256:$hash",
  "size": "$len"
}
EOF
}

build_for_arch() {
	local os=$1
	local arch=$2
	local plat=$3

	if [ "$os" == "windows" ]; then
		app_ext=".exe"
		pkg_ext=".zip"
		pkg_cmd="zip -qr"
	else
		app_ext=""
		pkg_ext=".tar.gz"
		pkg_cmd="tar -czf"
	fi

	local tool_stem="$DIR/$TOOL_NAME-$VERSION"
	local build_dir="$tool_stem/$plat"
	local build_file="$TOOL_NAME$app_ext"
	local package_file="$tool_stem-$plat$pkg_ext"

	echo "Building $TOOL_NAME for $os/$arch ($plat)"
	mkdir -p "$build_dir"
	(cd $BASE_DIR/extra/$TOOL_NAME && GOOS="$os" GOARCH="$arch" go build -o "$build_dir/$build_file")
	(cd "$tool_stem" && $pkg_cmd "$package_file" $plat/)
	hash_file $plat "$package_file" > $build_dir.json
}

build_json() {
	temp_file=$(mktemp)
	echo "{ \"packages\": [ { \"tools\": [ { \"name\": \"$TOOL_NAME\", \"version\": \"$VERSION\", \"systems\":" > $temp_file
	ls $DIR/$TOOL_NAME-$VERSION/*.json | sort | xargs cat | jq -s . >> $temp_file
	echo "} ] } ] }" >> $temp_file
	jq . $temp_file > $DIR/$TOOL_NAME-$VERSION.json
	rm -f $temp_file $DIR/$TOOL_NAME-$VERSION/*.json
}

build_for_arch "linux" "amd64" "x86_64-linux-gnu"
build_for_arch "linux" "arm64" "aarch64-linux-gnu"
build_for_arch "darwin" "amd64" "i386-apple-darwin11"
build_for_arch "windows" "386" "i686-mingw32"
build_json
echo "Build completed for $TOOL_NAME $VERSION: $DIR/$TOOL_NAME-$VERSION.json"
