#!/bin/bash

if [ -z "$CORE_TAG" ]; then
  echo "This script can be used in Github CI only."
  exit 1
fi

cat extra/zephyr-core-template.json | sed \
	-e "s/__CORE_TAG__/$CORE_TAG/" \
	-e "s/__ARTIFACT_FILE__/$ARTIFACT_FILE/" \
	-e "s/__ARTIFACT_HASH__/$(sha256sum $ARTIFACT_FILE | awk '{print $1}')/" \
	-e "s/__ARTIFACT_SIZE__/$(stat -c %s $ARTIFACT_FILE)/" \
	> $PACKAGE_INDEX_JSON
