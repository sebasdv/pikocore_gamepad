#!/usr/bin/env bash
# sim/web/build.sh
set -euo pipefail
# This script lives in sim/web/. SIM_ROOT is sim/ (one level up from here) —
# all the $SIM_ROOT/core, $SIM_ROOT/runtime, $SIM_ROOT/web paths below assume
# that, matching sim/CMakeLists.txt's own SIM_ROOT convention.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SIM_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PIKO_ROOT="$(cd "$SIM_ROOT/.." && pwd)"
OUT_DIR="$PIKO_ROOT/web/public/sim"
mkdir -p "$OUT_DIR"

# On some machines (e.g. Windows with the Microsoft Store Python stub on PATH),
# a bare `python3` doesn't resolve to a real interpreter. Reuse EMSDK_PYTHON
# (already required for em++ itself on those machines) when it's set, falling
# back to `python3` on PATH otherwise.
PYTHON_BIN="${EMSDK_PYTHON:-python3}"

GEN_DIR="$(mktemp -d)"
mkdir -p "$GEN_DIR/doth"
"$PYTHON_BIN" - "$PIKO_ROOT/doth/easing.h" "$GEN_DIR/doth/easing.h" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
content = open(src, encoding="utf-8").read()
content = content.replace("} else if (", "}\n  if (")
assert "else" not in content, f"{src} has a bare 'else': flattening is unsafe"
open(dst, "w", encoding="utf-8").write(content)
PY

# piko_fw's C++ sources. NOTE: unlike CMake's native build (project(... C CXX), which
# picks the compiler per file by extension), a single `em++` invocation with interspersed
# `-x c`/`-x c++` switches does NOT scope each switch to the files that follow it the way
# a direct clang invocation would: emcc.py collects every `-x` flag on the command line and
# re-emits all of them (in original order) ahead of each per-file compile it runs internally,
# so the LAST `-x` on the whole command line wins for every input file, not just the ones
# positioned after it. ui.cpp includes LCD_1in3.h/GUI_Paint.h inside an `extern "C" { ... }`
# block, so it expects C-linkage symbols for the LCD/Paint/font .c files below — compiling
# those as C++ (silently, with no diagnostic, because of the above) mangles their symbol
# names and the link fails with "undefined symbol: LCD_1IN3_Init" etc. even though the
# sources compile without error. Work around this the same way CMake does it structurally:
# compile the C sources with `emcc` (which defaults to C, not C++) into their own object
# files, compile the C++ sources with `em++` into theirs, then link everything in a final
# `em++` call that does no compilation of its own. Keep any future gamepi13 .c file in
# FW_C_SOURCES and any future .cpp file in one of the *_CXX_SOURCES / CORE_SOURCES /
# RUNTIME_SOURCES arrays below.
FW_CXX_SOURCES=(
  "$PIKO_ROOT/src/main.cpp"
  "$PIKO_ROOT/src/PikoAudioBank.cpp"
  "$PIKO_ROOT/src/gamepi13/ui.cpp"
)
FW_C_SOURCES=(
  "$PIKO_ROOT/src/gamepi13/dev_shim.c"
  "$PIKO_ROOT/src/gamepi13/lcd/LCD_1in3.c"
  "$PIKO_ROOT/src/gamepi13/lcd/GUI_Paint.c"
  "$PIKO_ROOT/src/gamepi13/lcd/font12.c"
  "$PIKO_ROOT/src/gamepi13/lcd/font16.c"
  "$PIKO_ROOT/src/gamepi13/lcd/font20.c"
  "$PIKO_ROOT/src/gamepi13/lcd/font24.c"
)
CORE_SOURCES=(
  "$SIM_ROOT/core/st7789.cpp"
  "$SIM_ROOT/core/pwm_dac.cpp"
  "$SIM_ROOT/core/flash_store.cpp"
  "$SIM_ROOT/core/bank_file.cpp"
  "$SIM_ROOT/core/buttons.cpp"
  "$SIM_ROOT/core/press_script.cpp"
  "$SIM_ROOT/core/pacing.cpp"
)
RUNTIME_SOURCES=(
  "$SIM_ROOT/web/fiber_shim.cpp"
  "$SIM_ROOT/runtime/sim_hal.cpp"
  "$SIM_ROOT/runtime/firmware_glue.cpp"
  "$SIM_ROOT/runtime/bank_hotload.cpp"
  "$SIM_ROOT/web/main.cpp"
)

FW_DEFINES=(
  -DPIKO_GAMEPI13=1 -DPIKO_GAMEPI13_SD=0 -DPIKO_SIM=1 -DPIKO_FIRMWARE_RESERVE=524288u
  -DWS2812_ENABLED=1 -DMIDI_IN_ENABLED=0 -DMIDI_RESET_EVERY_BEAT=16 -DMIDI_CLOCK_MULTIPLIER=2
  -DMIDI_NOTE_KEY=0 -DPCB_V2_LAYOUT=0
)
INCLUDES=(
  -I "$SIM_ROOT/shim" -I "$GEN_DIR" -I "$PIKO_ROOT" -I "$PIKO_ROOT/src"
  -I "$PIKO_ROOT/src/gamepi13" -I "$PIKO_ROOT/src/gamepi13/lcd" -I "$SIM_ROOT"
)

OBJ_DIR="$(mktemp -d)"
OBJECTS=()
compile_one() {
  # $1 = compiler (emcc|em++), $2 = std flag (or "" for C default), $3 = source path
  local compiler="$1" std_flag="$2" src="$3"
  local obj="$OBJ_DIR/obj_${#OBJECTS[@]}_$(basename "$src").o"
  if [ -n "$std_flag" ]; then
    "$compiler" "$std_flag" -O2 "${INCLUDES[@]}" "${FW_DEFINES[@]}" -Dmain=piko_firmware_main \
      -c "$src" -o "$obj"
  else
    "$compiler" -O2 "${INCLUDES[@]}" "${FW_DEFINES[@]}" -Dmain=piko_firmware_main \
      -c "$src" -o "$obj"
  fi
  OBJECTS+=("$obj")
}

for src in "${FW_CXX_SOURCES[@]}"; do compile_one em++ -std=c++20 "$src"; done
for src in "${FW_C_SOURCES[@]}"; do compile_one emcc "" "$src"; done
for src in "${CORE_SOURCES[@]}"; do compile_one em++ -std=c++20 "$src"; done
for src in "${RUNTIME_SOURCES[@]}"; do compile_one em++ -std=c++20 "$src"; done

em++ -O2 -sASYNCIFY -sASYNCIFY_STACK_SIZE=131072 \
  "${OBJECTS[@]}" \
  -sMODULARIZE=1 -sEXPORT_ES6=1 -sEXPORT_NAME=createPikoSimModule \
  -sEXPORTED_FUNCTIONS=_piko_init,_piko_step,_piko_snapshot_lcd,_piko_lcd_ptr,_piko_set_buttons,_piko_map_xinput,_piko_pull_audio,_piko_speed,_malloc,_free \
  -sEXPORTED_RUNTIME_METHODS=ccall,cwrap,HEAPU8,HEAPU16,HEAPF32 \
  -sALLOW_MEMORY_GROWTH=1 \
  -o "$OUT_DIR/pikocore_sim.js"

cp "$PIKO_ROOT/build-sim/bin/amen_pad_bank.pikobank" "$OUT_DIR/amen_pad_bank.pikobank"
echo "Built $OUT_DIR/pikocore_sim.js + amen_pad_bank.pikobank"
