#!/bin/bash

python3 microc.py $1 
clang  ${1%.*}.ll main-${1%.*}.c -o ${1%.*}

