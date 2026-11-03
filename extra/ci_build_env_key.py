#!/usr/bin/env python3

# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# Script to compute the Actions cache key of the CI build environment.
#
# The build environment depends on the exact revisions of the west projects:
# the revisions in the manifest that are not already SHAs (such as branches or
# tags) are resolved with 'git ls-remote'. The projects imported from those
# need no lookup, as Zephyr's own manifest pins all of them by SHA.
#
# The key is a hash of the resolved revisions and of the contents of all the
# given files, which must include the manifest and anything else affecting
# how the environment is set up. The resolved revisions are printed to stderr.
#
# Usage: ci_build_env_key.py <west.yml> [<file>...]

import hashlib
import re
import subprocess
import sys

import yaml

def project_url(project, manifest):
    if 'url' in project:
        return project['url']
    remote_name = project.get('remote', manifest.get('defaults', {}).get('remote'))
    remote = next(r for r in manifest.get('remotes', []) if r['name'] == remote_name)
    return f"{remote['url-base']}/{project.get('repo-path', project['name'])}"

def resolve_revision(url, rev):
    if re.fullmatch(r'[0-9a-f]{40}', rev):
        return rev
    # prefer tags (peeled to their commit) over branches
    candidates = [f"refs/tags/{rev}^{{}}", f"refs/tags/{rev}", f"refs/heads/{rev}"]
    output = subprocess.run(['git', 'ls-remote', url, *candidates],
                            capture_output=True, text=True, check=True).stdout
    refs = {}
    for line in output.splitlines():
        sha, ref = line.split('\t')
        refs[ref] = sha
    for ref in candidates:
        if ref in refs:
            return refs[ref]
    sys.exit(f"::error::Cannot resolve revision '{rev}' of {url}")

def main():
    if len(sys.argv) < 2:
        sys.exit(f"Usage: {sys.argv[0]} <west.yml> [<file>...]")

    with open(sys.argv[1]) as f:
        manifest = yaml.safe_load(f)['manifest']

    key_hash = hashlib.sha256()
    default_rev = manifest.get('defaults', {}).get('revision', 'main')
    for project in manifest['projects']:
        url = project_url(project, manifest)
        sha = resolve_revision(url, project.get('revision', default_rev))
        print(f"{project['name']} {sha}", file=sys.stderr)
        key_hash.update(f"{project['name']} {sha}\n".encode())

    for path in sys.argv[1:]:
        with open(path, 'rb') as f:
            key_hash.update(f.read())

    print(f"build-env-{key_hash.hexdigest()[:40]}")

if __name__ == '__main__':
    main()
