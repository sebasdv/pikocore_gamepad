#!/usr/bin/env bash
# sim/web/build.sh
set -euo pipefail
cd "$(dirname "$0")"
OUT_DIR=../../web/public/sim
mkdir -p "$OUT_DIR"

em++ -std=c++20 -O2 \
  hello.cpp \
  -sMODULARIZE=1 -sEXPORT_ES6=1 -sEXPORT_NAME=createPikoSimModule \
  -sEXPORTED_FUNCTIONS=_piko_hello,_main \
  -sEXPORTED_RUNTIME_METHODS=ccall,cwrap \
  -o "$OUT_DIR/pikocore_sim.js"

echo "Built $OUT_DIR/pikocore_sim.js"
