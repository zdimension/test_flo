# coding: utf-8
import enum
from dataclasses import dataclass, field

from lark import Token
from more_itertools import partition


def analyze(tree):
    assert tree.data == "programme"
    main = Function("_main", Type.VOID, [])
    scope = GLOBAL_SCOPE.child()
    scope.parent_function = main
    Analyzer(scope).analyze_bloc(tree)
    tree.scope = scope


class Type(enum.IntFlag):
    INTEGER = enum.auto()
    BOOLEAN = enum.auto()
    VOID = enum.auto()

    @staticmethod
    def from_str(s):
        if s == "entier":
            return Type.INTEGER
        elif s == "booleen":
            return Type.BOOLEAN
        else:
            raise ValueError(s)

    def size(self):
        if self == Type.INTEGER:
            return 4
        elif self == Type.BOOLEAN:
            return 4
        else:
            raise ValueError(self)


@dataclass
class Variable:
    type: Type
    offset: int


@dataclass
class Function:
    name: str
    return_type: Type
    args: list[tuple[str, Type]]
    stack_size: int = 0


@dataclass
class Scope:
    functions: dict[str, Function] = field(default_factory=dict)
    variables: dict[str, Variable] = field(default_factory=dict)
    parent: "Scope" = None
    parent_function: Function = None
    offset: int = 0

    def get_function(self, name):
        if here := self.functions.get(name):
            return here
        elif self.parent is not None:
            return self.parent.get_function(name)
        else:
            raise ValueError(name)

    def get_variable(self, name):
        if here := self.variables.get(name):
            return here.type
        elif self.parent is not None:
            return self.parent.get_variable(name)
        else:
            raise ValueError(name)

    def get_offset(self, name):
        if here := self.variables.get(name):
            return self.offset + here.offset + here.type.size()
        elif self.parent is not None:
            return self.parent.get_offset(name)
        else:
            raise ValueError(name)

    def child(self):
        return Scope(parent=self, parent_function=self.parent_function, offset=self.next_address())

    def stack_size(self):
        if self.parent_function is None:
            return 0
        else:
            return self.parent.stack_size() + self.next_address()

    def next_address(self):
        if self.variables:
            last_var = next(reversed(self.variables.values()))
            return last_var.offset + last_var.type.size()
        else:
            return 0

    def declare(self, name, type):
        self.variables[name] = Variable(type, self.next_address())
        self.parent_function.stack_size = max(self.parent_function.stack_size, self.stack_size())


GLOBAL_SCOPE = Scope({
    "ecrire": Function("ecrire", Type.VOID, [("valeur", Type.INTEGER | Type.BOOLEAN)]),
    "lire": Function("lire", Type.INTEGER, []),
})


@dataclass
class Analyzer:
    scope: Scope

    def analyze(self, tree):
        if type(tree) == Token:
            ty = getattr(self, "analyze_" + tree.type)(tree)
        else:
            ty = getattr(self, "analyze_" + tree.data)(tree)
            tree.type = ty
        return ty

    def analyze_ENTIER(self, entier):
        return Type.INTEGER

    def analyze_BOOLEEN(self, booleen):
        return Type.BOOLEAN

    def analyze_affectation(self, affectation):
        var, val = affectation.children
        assert self.analyze(var) == self.analyze(val)

    def analyze_NOM(self, nom):
        return self.scope.get_variable(nom.value)

    def analyze_bloc(self, block):
        items = block.children
        stmts, funcs = map(list, partition(lambda i: i.data == "fonction", items))
        for func in funcs:
            returns, name, args, body = func.children
            func_obj = Function(
                name.value,
                Type.from_str(returns),
                [
                    (arg.children[1].value, Type.from_str(arg.children[0])) for arg in args.children
                ] if args else []
            )
            self.scope.functions[name.value] = func_obj
            func.func_obj = func_obj
        for func in funcs:
            _, _, _, body = func.children
            scope = self.scope.child()
            scope.parent_function = func.func_obj
            for name, type in reversed(func.func_obj.args):
                scope.declare(name, type)
            scope.declare("$ra", Type.INTEGER)
            scope.declare("$old_ebp", Type.INTEGER)
            scope.offset = -func.func_obj.stack_size
            func.func_obj.stack_size = 0
            func.scope = scope
            body_scope = scope.child()
            body_scope.offset = scope.next_address() + scope.offset
            func.body_scope = body_scope
            Analyzer(body_scope).analyze_bloc(body)
        for stmt in stmts:
            self.analyze(stmt)
        block.code = stmts, funcs
        block.scope = self.scope

    def analyze_expr_instr(self, expr):
        self.analyze(expr.children[0])

    def analyze_si(self, si):
        cond, body, *orelse = si.children
        assert self.analyze(cond) == Type.BOOLEAN
        Analyzer(self.scope.child()).analyze_bloc(body)
        if orelse:
            Analyzer(self.scope.child()).analyze(orelse[0])

    def analyze_tantque(self, tq):
        cond, body = tq.children
        assert self.analyze(cond) == Type.BOOLEAN
        Analyzer(self.scope.child()).analyze_bloc(body)

    def analyze_decl(self, decl):
        type, name, val = decl.children
        type = Type.from_str(type.value)
        if val:
            assert type == self.analyze(val)
        self.scope.declare(name.value, type)

    def analyze_retourner(self, ret):
        assert self.scope.parent_function.return_type == self.analyze(ret.children[0])

    def analyze_variable(self, var):
        name = var.children[0].value
        return self.scope.get_variable(name)

    def analyze_expr_add(self, expr):
        first, op, second = expr.children
        type = self.analyze(first)
        assert type in {Type.INTEGER}
        assert type == self.analyze(second)
        return type

    def analyze_appel(self, appel):
        func, args = appel.children
        args = args.children if args else []
        assert func.type == "NOM"
        func = func.value
        func_obj = self.scope.get_function(func)
        assert len(args) == len(
            func_obj.args), f"Appel de {func} avec {len(args)} arguments au lieu de {len(func_obj.args)}"
        for arg, (_, type) in zip(args, func_obj.args):
            assert self.analyze(arg) in type, f"Argument {arg} de type {self.analyze(arg)} au lieu de {type}"
        return func_obj.return_type

    def analyze_expr_mul(self, expr):
        first, op, second = expr.children
        type = self.analyze(first)
        assert type in {Type.INTEGER}
        assert type == self.analyze(second)
        return type

    def analyze_expr_rel(self, expr):
        first, op, second = expr.children
        type = self.analyze(first)
        assert type in {Type.INTEGER}
        assert type == self.analyze(second)
        return Type.BOOLEAN

    def analyze_expr_unaire(self, expr):
        op, val = expr.children
        type = self.analyze(val)
        if op == "non":
            assert type == Type.BOOLEAN
        elif op == "-":
            assert type == Type.INTEGER
        return type

    def analyze_expr_mult(self, expr):
        first, op, second = expr.children
        type = self.analyze(first)
        assert type in {Type.INTEGER}
        assert type == self.analyze(second)
        return type

    def analyze_expr_ou(self, expr):
        first, second = expr.children
        type = self.analyze(first)
        assert type in {Type.BOOLEAN}
        assert type == self.analyze(second)
        return type

    def analyze_expr_et(self, expr):
        first, second = expr.children
        type = self.analyze(first)
        assert type in {Type.BOOLEAN}
        assert type == self.analyze(second)
        return type

    def analyze_expr_non(self, expr):
        val = expr.children[1]
        type = self.analyze(val)
        assert type in {Type.BOOLEAN}
        return type
