#!/usr/bin/env python3

# Copyright (c) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: Apache-2.0

# Rebuild ld --print-memory-usage table from a GNU ld map file.
# usage: map_memusage.py [--json FILE] [--set-used REGION VALUE]
#                        [--set-max REGION VALUE] [--delete REGION]
#                        zephyr.map zephyr.elf
# --json also writes { "<region>": [used, size], ... } to FILE
# (same shape as ci_shared meminfo).
# --set-used/--set-max override a region's used/total size after the map
# is parsed, adding the region if missing; --delete removes a region.
# All three can be repeated.
#
# "Used" is region length minus the biggest free span, so fragmented
# placement (e.g. data at both ends of a region) shows as unusable space.
# Output sections count at their VMA and, if different, at their LMA.
# *fill* padding inside output sections (e.g. from ". = ADDR") counts as
# free at the VMA; at the LMA it is real bytes in the image.
# The map has no section flags, so the ELF from the same link is used to
# skip non-alloc sections (.debug*, (INFO) sections, etc.).
import argparse, json, re, sys

from elftools.elf.constants import SH_FLAGS
from elftools.elf.elffile import ELFFile

ap = argparse.ArgumentParser()
ap.add_argument('map')
ap.add_argument('elf')
ap.add_argument('--json', metavar='FILE', help='also write [used, size] per region as JSON')
ap.add_argument('--set-used', nargs=2, action='append', default=[], metavar=('REGION', 'VALUE'),
                help='override the used size of REGION')
ap.add_argument('--set-max', nargs=2, action='append', default=[], metavar=('REGION', 'VALUE'),
                help='override the total size of REGION')
ap.add_argument('--delete', action='append', default=[], metavar='REGION',
                help='remove REGION from the report')
args = ap.parse_args()

lines = open(args.map).read().splitlines()

with open(args.elf, 'rb') as f:
    alloc = { s.name for s in ELFFile(f).iter_sections() if s['sh_flags'] & SH_FLAGS.SHF_ALLOC }

OCC, FILL = 2, 3
regions = {}
i = lines.index('Memory Configuration') + 3
while lines[i].strip():
    f = lines[i].split()
    if f[0] != '*default*':
        # origin, length, occupied spans, fill spans
        regions[f[0]] = [int(f[1], 16), int(f[2], 16), [], []]
    i += 1

def add(addr, size, kind):
    # first match wins, like a linker script listing regions in order
    for r in regions.values():
        if r[0] <= addr < r[0] + r[1]:
            r[kind].append((addr, min(addr + size, r[0] + r[1])))
            return

out = re.compile(r'^(\S+)?\s+0x([0-9a-f]+)\s+0x([0-9a-f]+)(?:\s+load address 0x([0-9a-f]+))?\s*$')
fill = re.compile(r'^ \*fill\*\s+0x([0-9a-f]+)\s+0x([0-9a-f]+)')
name = None
counted = False  # inside an output section that was counted
for l in lines[lines.index('Linker script and memory map'):]:
    if l and not l[0].isspace():
        # top-level output section; long names wrap addr/size to next line
        counted = False
        m = out.match(l)
        if m:
            name = m[1]
        else:
            name = l if re.fullmatch(r'\S+', l) else None
            continue
    elif name and l.startswith(' ' * 16):
        m = out.match(l)
        if not m or m[1]:
            name = None
            continue
    else:
        name = None
        if counted and (m := fill.match(l)):
            add(int(m[1], 16), int(m[2], 16), FILL)
        continue
    vma, size, lma = int(m[2], 16), int(m[3], 16), m[4]
    if size and name in alloc:
        counted = True
        add(vma, size, OCC)
        if lma is not None and int(lma, 16) != vma:
            add(int(lma, 16), size, OCC)
    name = None

report = {}
for n, (o, l, occ, fills) in regions.items():
    free, cur = [], o
    for start, end in sorted(occ):
        if start > cur:
            free.append((cur, start))
        cur = max(cur, end)
    if o + l > cur:
        free.append((cur, o + l))
    gap, span = 0, None
    for start, end in sorted(free + fills):
        if span and start <= span[1]:
            span[1] = max(span[1], end)
        else:
            span = [start, end]
        gap = max(gap, span[1] - span[0])
    u = l - gap
    report[n] = [u, l]

for idx, opts in ((0, args.set_used), (1, args.set_max)):
    for n, v in opts:
        report.setdefault(n, [0, 0])[idx] = int(v, 0)
for n in args.delete:
    report.pop(n, None)

print(f"{'Memory region':>16} {'Used Size':>12} {'Region Size':>12}  %age Used")
for n, (u, l) in report.items():
    print(f"{n+':':>16} {u:>10} B {l:>10} B {100*u/l if l else 0:>9.2f}%")

if args.json:
    with open(args.json, 'w') as f:
        json.dump(report, f, indent=2)
        f.write('\n')
