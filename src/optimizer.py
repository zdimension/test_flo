# coding: utf-8
from __future__ import annotations

import dataclasses
import inspect
import sys
from types import UnionType
from typing import get_type_hints

from src.compiler import Program
from src.x86 import *

py_print = print
print = lambda *args: py_print(inspect.stack()[1].function, ":", *args, file=sys.stderr)


def type_in(needle, haystack):
    if isinstance(haystack, UnionType):
        return isinstance(needle, haystack.__args__)
    return isinstance(needle, haystack)


def optimize(prog: Program):
    pass_count = 0
    while any(pass_(prog) for pass_ in passes):
        pass_count += 1
        if pass_count % 1000 == 0:
            print("Warning:", pass_count, "passes have been run, this may be an infinite loop")
    print("Optimization finished after", pass_count, "passes")


passes = []


def register_pass(pass_):
    passes.append(pass_)
    return pass_


@register_pass
def push_then_pop(prog: Program):
    found = False
    for i, (a, b) in enumerate(zip(prog.instrs, prog.instrs[1:])):
        if isinstance(a, push) and isinstance(b, pop):
            print(f"{a}; {b} => {mov(b.dst, a.src)}")
            prog.instrs[i:i + 2] = [mov(b.dst, a.src), nop()]
            found = True
    return found


@register_pass
def redundant_mov(prog: Program):
    found = False
    for i, a in enumerate(prog.instrs):
        if isinstance(a, mov) and a.src == a.dst:
            print(f"{a} => nop")
            prog.instrs[i] = nop()
            found = True
    return found


@register_pass
def remove_nops(prog: Program):
    old_instrs = prog.instrs
    prog.instrs = [instr for instr in old_instrs if not isinstance(instr, nop)]
    return len(prog.instrs) != len(old_instrs)


@register_pass
def jump_right_after(prog: Program):
    found = False
    for i, (a, b) in enumerate(zip(prog.instrs, prog.instrs[1:])):
        if isinstance(a, jmp) and isinstance(b, label) and a.dst == b:
            print(f"{a}; {b} => nop; {b}")
            prog.instrs[i] = nop()
            found = True
    return found


@register_pass
def unused_label(prog: Program):
    labels = prog.labels.copy()
    labels.pop("_start", None)
    for instr in prog.instrs:
        if not isinstance(instr, label):
            for v in instr.__dict__.values():
                if isinstance(v, label):
                    labels.pop(v.name, None)
                elif isinstance(v, str):
                    labels.pop(v, None)
    for name, instr in labels.items():
        print(f"Unused label: {name}")
        prog.instrs.remove(instr)
        del prog.labels[name]
    return len(labels) > 0


@register_pass
def label_right_after(prog: Program):
    def rename(old_label: label, new_label: label):
        for i, instr in enumerate(prog.instrs):
            if not isinstance(instr, label):
                for k, v in instr.__dict__.items():
                    if v is old_label:
                        prog.instrs[i] = dataclasses.replace(instr, **{k: new_label})
                    elif isinstance(v, str) and v == old_label.name:
                        prog.instrs[i] = dataclasses.replace(instr, **{k: new_label.name})

    found = False
    for i, (a, b) in enumerate(zip(prog.instrs, prog.instrs[1:])):
        if isinstance(a, label) and isinstance(b, label):
            print(f"{a}; {b} => merge")
            prog.instrs[i + 1] = nop()
            rename(b, a)
            del prog.labels[b.name]
            found = True
    return found


@register_pass
def mov_pop_to_leave(prog: Program):
    found = False
    for i, (a, b) in enumerate(zip(prog.instrs, prog.instrs[1:])):
        if a == mov(r.esp, r.ebp) and b == pop(r.ebp):
            print(f"{a}; {b} => leave")
            prog.instrs[i:i + 2] = [leave(), nop()]
            found = True
    return found


@register_pass
def zero_add_sub(prog: Program):
    found = False
    for i, instr in enumerate(prog.instrs):
        if isinstance(instr, (add, sub)) and instr.src == imm(0):
            print(f"{instr} => nop")
            prog.instrs[i] = nop()
            found = True
    return found


@register_pass
def move_ab_ba(prog: Program):
    found = False
    for i, (a, b) in enumerate(zip(prog.instrs, prog.instrs[1:])):
        if isinstance(a, mov) and hasattr(b, "src") and a.dst == b.src and isinstance(a.src, (Register, Immediate)):
            src_type = get_type_hints(type(b))["src"]
            if type_in(a.src, src_type):
                new_instr = dataclasses.replace(b, src=a.src)
                print(f"{a}; {b} => {a}; {new_instr}")
                prog.instrs[i + 1] = new_instr
                found = True
    return found


@register_pass
def move_dead_writes(prog: Program):
    found = False
    write_targets = {}
    for i, instr in enumerate(prog.instrs):
        if isinstance(instr, (AltersFlow)):
            write_targets.clear()
            continue
        if isinstance(instr, mov):
            if write_i := write_targets.get(instr.dst, None):
                print(f"deleting dead {prog.instrs[write_i]}" + (" (replaced by " + str(instr) + ")"))
                prog.instrs[write_i] = nop()
                found = True
            write_targets[instr.dst] = i
        if (src := getattr(instr, "src", None)) in write_targets:
            write_targets.pop(src, None)
    return found
