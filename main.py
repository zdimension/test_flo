import sys
from glob import glob

from src.analyzer import analyze
from src.compiler import compile
from src.optimizer import optimize
from src.parser import parse


def process(code):
    tree = parse(code)
    analyze(tree)
    asm = compile(tree)
    return asm


def main(args):
    if False:
        for path in glob("input/*.flo"):
            with open(path) as fp:
                try:
                    tree = parse(fp.read())
                except Exception as e:
                    print(f"Error in {path}: {e}")
                    raise

    if len(args) < 2:
        print("usage: python3 main.py NOM_FICHIER_SOURCE.flo")
    else:
        with open(args[1], "r") as f:
            data = f.read()
        try:
            asm = process(data)
        except:
            raise
            print("Error in", args[1])
        with open(args[1].replace(".flo", "_raw.asm"), "w") as f:
            f.write(asm.asm())
        optimize(asm)
        with open(args[1].replace(".flo", ".asm"), "w") as f:
            f.write(asm.asm())


if __name__ == '__main__':
    main(sys.argv)
