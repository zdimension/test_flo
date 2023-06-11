#!/usr/bin/env bash

# input file
input_file=$1

if [ -z "$input_file" ]; then
    echo "Usage: ./run.sh <input_file>"
    exit 1
fi

python3 main.py $input_file.flo

if [ $? -ne 0 ]; then
    echo "main.py failed"
    exit 2
fi

nasm -f elf -g -F dwarf $input_file.asm

if [ $? -ne 0 ]; then
    echo "nasm failed"
    exit 3
fi

ld -m elf_i386 -o $input_file.exe $input_file.o

if [ $? -ne 0 ]; then
    echo "ld failed"
    exit 4
fi

ssh tom@ubuntu-nexedi "/mnt/hgfs/C/GitHub/test_flo/$input_file.exe 2>&1"