#!/usr/bin/env bash

if [ "$#" -ne 1 ]; then
    echo "$0 <path to dir with requirements.in>"
    exit 1
fi

arg=$1
d="${arg%%\/}"
p="$d/requirements.in"

if [ ! -f $p ]; then
    echo "File not found!"
    exit 1
fi

uv pip compile $p -o $d/requirements.txt
