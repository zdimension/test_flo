# coding: utf-8

from lark import Lark

with open("grammar.lark") as fp:
    parser = Lark(fp.read(), start="programme")


def parse(code):
    return parser.parse(code)
