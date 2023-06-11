#!/usr/bin/env bash

run() {
  printf "0\n1\n1\n0\n1\n1\n1\n1\n1\n1\n1\n1" | ./run.sh ${1%.*}
}

check() {
  echo $1
  diff -u ${1%.*}.out <(run $1 2>/dev/null)
  if [ $? -ne 0 ]; then
    echo "Test failed"
    exit 1
  fi
}

check_bad() {
  echo $1
  run $1 >/dev/null 2>/dev/null
  if [ $? -ne 2 ]; then
    echo "Test failed"
    exit 1
  fi
}

if [ $# -eq 1 ]; then
  check $1
  exit 0
fi

for file in input/*.flo
do
  check $file
done

for file in bad_input/*.flo
do
  check_bad $file
done