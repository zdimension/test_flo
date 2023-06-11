# coding: utf-8

import glob
import os

HEADER_LEN = 7

stats = []
for path in glob.glob("input/*.flo"):
    name = os.path.basename(path)[:-4]
    with open(f"input/{name}.asm", "r", encoding="utf-8") as f:
        lines_asm = f.readlines()[HEADER_LEN:]
    with open(f"input/{name}_raw.asm", "r", encoding="utf-8") as f:
        lines_asm_raw = f.readlines()[HEADER_LEN:]
    perc = (len(lines_asm_raw) - len(lines_asm)) / len(lines_asm_raw) * 100
    print(f"{name:20s}: {len(lines_asm_raw):3d} → {len(lines_asm):3d} lines: {perc:.2f}% reduction")
    stats.append(perc)
print(f"Average reduction: {sum(stats) / len(stats):.2f}%")
