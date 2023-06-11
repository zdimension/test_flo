# coding: utf-8
from dataclasses import field
from typing import List

from lark import Token

from src.analyzer import Scope, Type
from src.x86 import *


@dataclass
class Program:
    instrs: List[Instruction] = field(default_factory=list)
    label_count: int = 0
    labels: dict[str, label] = field(default_factory=dict)

    def asm(self):
        return "\n".join([
            '%include "io.asm"',
            "section .bss",
            "sinput: resb    255     ;reserve a 255 byte space in memory for the users input string",
            "v$a:    resd    1",
            "section .text",
            "global _start",
            *map(str, self.instrs),
        ])


def compile(prog):
    stmts, funcs = prog.code
    output = Program()
    comp = Compiler(output, prog.scope)
    for func in funcs:
        comp.compile_function(func)
    comp.compile_main(stmts)
    return output


@dataclass
class Compiler:
    program: Program
    scope: Scope

    def i(self, s: Instruction):
        self.program.instrs.append(s)
        if type(s) is label:
            if existing := self.program.labels.get(s.name):
                assert existing == s
            else:
                self.program.labels[s.name] = s

    def reserve_label(self, name):
        res = label(name)
        assert name not in self.program.labels
        self.program.labels[name] = res
        return res

    def compile_function(self, func):
        obj = func.func_obj
        _, _, _, body = func.children
        self.i(label(f"_{obj.name}"))
        end = self.reserve_label(f"{obj.name}_end")
        self.i(push(r.ebp))
        self.i(mov(r.ebp, r.esp))
        self.i(sub(r.esp, imm(obj.stack_size - func.body_scope.offset)))
        self.compile_bloc(body)
        self.i(end)
        self.i(mov(r.esp, r.ebp))
        self.i(pop(r.ebp))
        self.i(ret())

    def compile_main(self, main):
        self.i(label("_start"))
        self.i(push(r.ebp))
        self.i(mov(r.ebp, r.esp))
        self.i(sub(r.esp, imm(self.scope.parent_function.stack_size)))
        for stmt in main:
            self.compile(stmt)
        self.i(mov(r.eax, imm(1)))  # exit()
        self.i(mov(r.ebx, imm(0)))
        self.i(int_(0x80))

    def compile(self, tree):
        if type(tree) == Token:
            return getattr(self, "compile_" + tree.type)(tree)
        return getattr(self, "compile_" + tree.data)(tree)

    def compile_expr_add(self, expr):
        lhs, op, rhs = expr.children
        self.compile(lhs)
        self.compile(rhs)
        self.i(pop(r.ebx))
        self.i(pop(r.eax))
        if op == "+":
            self.i(add(r.eax, r.ebx))
        elif op == "-":
            self.i(sub(r.eax, r.ebx))
        self.i(push(r.eax))

    def compile_retourner(self, retourner):
        self.compile(retourner.children[0])
        self.i(pop(r.eax))
        self.i(jmp(self.get_label(f"{self.scope.parent_function.name}_end")))

    def get_label(self, name):
        if label := self.program.labels.get(name):
            return label
        raise Exception(f"Label {name} not found")

    def compile_appel(self, appel):
        nom, args = appel.children
        args = args.children if args else []
        if builtin := getattr(self, "builtin_" + nom.value, None):
            builtin(args)
            return
        func = self.scope.get_function(nom.value)
        for arg in reversed(args):
            self.compile(arg)
        self.i(call(f"_{nom.value}"))
        self.i(add(r.esp, imm(sum(type.size() for _, type in func.args))))
        if func.return_type != Type.VOID:
            self.i(push(r.eax))

    def builtin_lire(self, args):
        assert len(args) == 0
        self.i(mov(r.eax, Global("sinput")))
        self.i(call("readline"))
        self.i(call("atoi"))
        self.i(push(r.eax))

    def builtin_ecrire(self, args):
        assert len(args) == 1
        self.compile(args[0])
        self.i(pop(r.eax))
        self.i(call("iprintLF"))

    def compile_NOM(self, nom):
        # self.i(push(self.get_offset(nom.value)))
        self.i(mov(r.eax, self.get_offset(nom.value)))
        self.i(push(r.eax))

    def compile_expr_instr(self, expr):
        val = expr.children[0]
        self.compile(val)
        if val.type != Type.VOID:
            self.i(pop(r.eax))

    def compile_decl(self, decl):
        _, name, val = decl.children
        if val:
            self.compile(val)
            self.i(pop(r.eax))
        else:
            self.i(mov(r.eax, imm(0)))
        self.i(mov(self.get_offset(name.value), r.eax))

    def compile_bloc(self, block):
        comp = Compiler(self.program, block.scope)
        for stmt in block.children:
            comp.compile(stmt)

    def compile_ENTIER(self, entier):
        self.i(push(imm(entier.value)))

    def compile_affectation(self, affectation):
        var, val = affectation.children
        self.compile(val)
        self.i(pop(r.eax))
        self.i(mov(self.get_offset(var.value), r.eax))

    def compile_expr_rel(self, expr):
        lhs, op, rhs = expr.children
        self.compile(lhs)
        self.compile(rhs)
        self.i(pop(r.ebx))
        self.i(pop(r.ecx))
        self.i(cmp(r.ecx, r.ebx))
        if op == "==":
            self.i(sete(r.al))
        elif op == "!=":
            self.i(setne(r.al))
        elif op == "<":
            self.i(setl(r.al))
        elif op == "<=":
            self.i(setle(r.al))
        elif op == ">":
            self.i(setg(r.al))
        elif op == ">=":
            self.i(setge(r.al))
        self.i(movzx(r.eax, r.al))
        self.i(push(r.eax))

    def get_offset(self, name) -> Memory:
        off = -self.scope.get_offset(name)
        return Memory(r.ebp, off)

    def compile_si(self, si):
        cond, if_block, *else_block = si.children
        self.compile(cond)
        self.i(pop(r.eax))
        self.i(cmp(r.eax, imm(0)))
        orelse = self.new_label()
        self.i(je(orelse))
        self.compile(if_block)
        endif = self.new_label()
        self.i(jmp(endif))
        self.i(orelse)
        if else_block:
            self.compile(else_block[0])
        self.i(endif)

    def compile_tantque(self, tantque):
        cond, block = tantque.children
        start = self.new_label()
        end = self.new_label()
        self.i(start)
        self.compile(cond)
        self.i(pop(r.eax))
        self.i(cmp(r.eax, imm(0)))
        self.i(je(end))
        self.compile(block)
        self.i(jmp(start))
        self.i(end)

    def compile_expr_unaire(self, expr):
        op, val = expr.children
        self.compile(val)
        self.i(pop(r.eax))
        if op == "-":
            self.i(neg(r.eax))
        else:
            raise NotImplementedError
        self.i(push(r.eax))

    def compile_expr_non(self, expr):
        self.compile(expr.children[1])
        self.i(pop(r.eax))
        self.i(cmp(r.eax, imm(0)))
        self.i(sete(r.al))
        self.i(movzx(r.eax, r.al))
        self.i(push(r.eax))

    def compile_expr_mult(self, expr):
        lhs, op, rhs = expr.children
        self.compile(lhs)
        self.compile(rhs)
        self.i(pop(r.ebx))
        self.i(pop(r.eax))
        if op == "*":
            self.i(imul(r.eax, r.ebx))
        elif op == "/":
            self.i(mov(r.edx, imm(0)))
            self.i(idiv(r.ebx))
        elif op == "%":
            self.i(mov(r.edx, imm(0)))
            self.i(idiv(r.ebx))
            self.i(mov(r.eax, r.edx))
        self.i(push(r.eax))

    def compile_BOOLEEN(self, bool):
        self.i(push(imm(1 if bool.value == "Vrai" else 0)))

    def new_label(self):
        self.program.label_count += 1
        return self.reserve_label(f"l{self.program.label_count}")

    def compile_expr_ou(self, expr):
        lhs, rhs = expr.children
        self.compile(lhs)
        self.compile(rhs)
        self.i(pop(r.ebx))
        self.i(pop(r.eax))
        self.i(or_(r.eax, r.ebx))
        self.i(setne(r.al))
        self.i(movzx(r.eax, r.al))
        self.i(push(r.eax))

    def compile_expr_et(self, expr):
        lhs, rhs = expr.children
        self.compile(lhs)
        self.compile(rhs)
        self.i(pop(r.eax))
        self.i(cmp(r.eax, imm(0)))
        self.i(setne(r.al))
        self.i(pop(r.ecx))
        self.i(cmp(r.ecx, imm(0)))
        self.i(setne(r.cl))
        self.i(and_(r.cl, r.al))
        self.i(movzx(r.eax, r.cl))
        self.i(push(r.eax))
