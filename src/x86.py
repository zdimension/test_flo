# coding: utf-8
from __future__ import annotations

from dataclasses import dataclass
from typing import Union, Optional

frozendata = lambda x: dataclass(frozen=True)(x)


@dataclass(init=False)
class Register:
    name: str

    def __set_name__(self, owner, name):
        self.name = name

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)


class r:
    al = Register()
    eax = Register()
    ebx = Register()
    ecx = Register()
    cl = Register()
    edx = Register()
    ebp = Register()
    esp = Register()


@frozendata
class Memory:
    base: Register
    offset: int = 0
    index_scale: Optional[(Register, Union[1, 2, 4, 8])] = None

    def __str__(self):
        items = str(self.base)
        if self.index_scale:
            index, scale = self.index_scale
            items += "+"
            items += str(index)
            if scale != 1:
                items += "*" + str(scale)
        if self.offset:
            if self.offset > 0:
                items += "+"
            items += str(self.offset)
        return f"dword [{items}]"


@frozendata
class Immediate:
    pass


@frozendata
class imm(Immediate):
    value: int

    def __str__(self):
        return str(self.value)


@frozendata
class Global(Immediate):
    name: str

    def __str__(self):
        return self.name


@frozendata
class Instruction:
    pass


@frozendata
class AltersFlow(Instruction):
    pass


@frozendata
class label(Instruction):
    name: str

    def __str__(self):
        return f"{self.name}:"


@frozendata
class mov(Instruction):
    dst: Register | Memory
    src: Register | Memory | Immediate

    def __str__(self):
        return f"mov {self.dst}, {self.src}"


@frozendata
class int_(Instruction):
    value: int

    def __str__(self):
        return f"int 0x{self.value:02x}"


@frozendata
class add(Instruction):
    dst: Register | Memory
    src: Register | Memory | Immediate

    def __str__(self):
        return f"add {self.dst}, {self.src}"


@frozendata
class sub(Instruction):
    dst: Register | Memory
    src: Register | Memory | Immediate

    def __str__(self):
        return f"sub {self.dst}, {self.src}"


@frozendata
class cmp(Instruction):
    dst: Register | Memory
    src: Register | Memory | Immediate

    def __str__(self):
        return f"cmp {self.dst}, {self.src}"


@frozendata
class push(Instruction):
    src: Register | Memory | Immediate

    def __str__(self):
        return f"push {self.src}"


@frozendata
class pop(Instruction):
    dst: Register | Memory

    def __str__(self):
        return f"pop {self.dst}"


@frozendata
class ret(Instruction):
    def __str__(self):
        return "ret"


@frozendata
class call(AltersFlow):
    dst: str

    def __str__(self):
        return f"call {self.dst}"


@frozendata
class jmp(AltersFlow):
    dst: label

    def __str__(self):
        return f"jmp {self.dst.name}"


@frozendata
class sete(Instruction):
    dst: Register | Memory

    def __str__(self):
        return f"sete {self.dst}"


@frozendata
class setne(Instruction):
    dst: Register | Memory

    def __str__(self):
        return f"setne {self.dst}"


@frozendata
class setl(Instruction):
    dst: Register | Memory

    def __str__(self):
        return f"setl {self.dst}"


@frozendata
class setle(Instruction):
    dst: Register | Memory

    def __str__(self):
        return f"setle {self.dst}"


@frozendata
class setg(Instruction):
    dst: Register | Memory

    def __str__(self):
        return f"setg {self.dst}"


@frozendata
class setge(Instruction):
    dst: Register | Memory

    def __str__(self):
        return f"setge {self.dst}"


@frozendata
class movzx(Instruction):
    dst: Register | Memory
    src: Register | Memory

    def __str__(self):
        return f"movzx {self.dst}, {self.src}"


@frozendata
class je(AltersFlow):
    dst: label

    def __str__(self):
        return f"je {self.dst.name}"


@frozendata
class neg(Instruction):
    dst: Register | Memory

    def __str__(self):
        return f"neg {self.dst}"


@frozendata
class imul(Instruction):
    dst: Register
    src: Register | Memory

    def __str__(self):
        return f"imul {self.dst}, {self.src}"


@frozendata
class idiv(Instruction):
    src: Register | Memory

    def __str__(self):
        return f"idiv {self.src}"


@frozendata
class or_(Instruction):
    dst: Register | Memory
    src: Register | Memory | Immediate

    def __str__(self):
        return f"or {self.dst}, {self.src}"


@frozendata
class and_(Instruction):
    dst: Register | Memory
    src: Register | Memory | Immediate

    def __str__(self):
        return f"and {self.dst}, {self.src}"


@frozendata
class nop(Instruction):
    def __str__(self):
        return "nop"


@frozendata
class leave(AltersFlow):
    def __str__(self):
        return "leave"
