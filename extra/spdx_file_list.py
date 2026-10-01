#!/usr/bin/env python

# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# List the files an image is built from, using the SPDX 3 documents generated
# by 'west spdx' for it (e.g. spdx/<variant>/loader, see extra/build.sh).
#
# Starting from the final image, the static links are followed to every
# library linked into it, and the build inputs of each of them are collected.
# Each file is printed with the package it belongs to: the '-sources' packages
# hold the files checked out in the workspace, the others the files generated
# during the build. Headers are only listed if 'west spdx' was run with
# --analyze-includes. When a package records its location in the west
# workspace (sourceInfo "west workspace path: <path>"), its files are printed
# with their workspace path.

import argparse
import collections
import glob
import json
import os
import posixpath
import sys

RELATIONSHIP_TYPES = ("Relationship", "LifecycleScopedRelationship")
FINAL_IMAGE_PACKAGE = "zephyr_final"
WORKSPACE_PATH_INFO = "west workspace path: "


def load_graph(image_dir):
    graph = []
    for path in sorted(glob.glob(os.path.join(image_dir, "*.jsonld"))):
        with open(path) as f:
            graph += json.load(f)["@graph"]
    return graph


def workspace_path(package, name):
    """Workspace path of a file of the package, if the package records it."""
    info = package.get("software_sourceInfo", "")
    if info.startswith(WORKSPACE_PATH_INFO):
        return posixpath.normpath(posixpath.join(info[len(WORKSPACE_PATH_INFO):], name))
    return None


def image_files(graph):
    """Return [(package name, file name, workspace path or None)] of the files
    the image is built from."""
    elements = {e["spdxId"]: e for e in graph if e.get("spdxId")}
    targets = collections.defaultdict(list)  # (from, type) -> [to]
    producer = {}  # artifact -> build that outputs it
    owner = {}  # file -> package that contains it
    for rel in graph:
        if rel.get("type") not in RELATIONSHIP_TYPES:
            continue
        targets[(rel["from"], rel["relationshipType"])] += rel["to"]
        for to in rel["to"]:
            if rel["relationshipType"] == "hasOutput":
                producer[to] = rel["from"]
            elif rel["relationshipType"] == "contains":
                owner[to] = rel["from"]

    finals = [e["spdxId"] for e in graph if e.get("type") == "software_Package" and e.get("name") == FINAL_IMAGE_PACKAGE]
    if not finals:
        sys.exit(f"no '{FINAL_IMAGE_PACKAGE}' package found: is this a 'west spdx' SPDX 3 image directory?")

    # artifacts in the image: the final image and everything statically
    # linked into it, recursively
    todo = [f for final in finals for f in targets[(final, "contains")]]
    artifacts = set()
    while todo:
        artifact = todo.pop()
        if artifact in artifacts:
            continue
        artifacts.add(artifact)
        todo += targets[(artifact, "hasStaticLink")]
        if artifact in owner:
            todo += targets[(owner[artifact], "hasStaticLink")]

    files = set()
    for artifact in artifacts:
        build = producer.get(artifact)
        if build:
            files |= {i for i in targets[(build, "hasInput")] if elements.get(i, {}).get("type") == "software_File"}

    def name(element_id):
        return elements.get(element_id, {}).get("name", element_id)

    result = []
    for f in files:
        package = elements.get(owner.get(f), {})
        result.append((package.get("name", ""), name(f), workspace_path(package, name(f))))
    return sorted(result)


def main():
    parser = argparse.ArgumentParser(description="List the files an image is built from, from its SPDX 3 documents.")
    parser.add_argument("image_dir", help="directory with the image SPDX 3 documents (e.g. spdx/<variant>/loader)")
    parser.add_argument("--sources-only", action="store_true", help="only list files of '-sources' packages")
    parser.add_argument("--json", action="store_true", help="print a JSON list of {package, file, path}")
    args = parser.parse_args()

    files = image_files(load_graph(args.image_dir))
    if args.sources_only:
        files = [f for f in files if f[0].endswith("-sources")]

    if args.json:
        json.dump(
            [{"package": package, "file": name, "path": path} for package, name, path in files],
            sys.stdout,
            indent=2,
        )
        print()
    else:
        for package, name, path in files:
            print(f"{package}\t{path or name}")


if __name__ == "__main__":
    main()
