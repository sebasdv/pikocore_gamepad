#!/bin/bash
set -e
cd "$(dirname "$0")"
mkdir -p logs
mkdir logs/ciclo.lock 2>/dev/null || { echo "OTRO CICLO CORRIENDO"; exit 9; }
trap 'rmdir logs/ciclo.lock' EXIT
KIPY="/c/Program Files/KiCad/9.0/bin/python.exe"
KICLI="/c/Program Files/KiCad/9.0/bin/kicad-cli.exe"
JAR="$HOME/Documents/KiCad/10.0/3rdparty/plugins/app_freerouting_kicad-plugin/jar/freerouting-2.4.1.jar"
abiertas() { python -c "import json;print(len(json.load(open('logs/drc.json',encoding='utf-8'))['unconnected_items']))"; }
drc() { "$KICLI" pcb drc --severity-all --schematic-parity --format json -o logs/drc.json pikocore_gamepad.kicad_pcb > /dev/null || true; }
"$KIPY" gen_sch.py > /dev/null
"$KICLI" sch export netlist -o pikocore_gamepad.net pikocore_gamepad.kicad_sch
# NUNCA por tuberia a grep: KiCad escupe miles de lineas por stderr (SWIG) y el
# pipe se traba a veces (route_io.py lo documenta; paso dos veces el 2026-10-15).
"$KIPY" gen_pcb.py > logs/gen_pcb.log 2>&1; grep -av swig logs/gen_pcb.log | tail -3
"$KIPY" manual_tracks.py > logs/manual.log 2>&1; grep -a "ERROR" logs/manual.log && exit 1
"$KIPY" plane_vias.py > logs/planes.log 2>&1; grep -a guardado logs/planes.log
"$KIPY" route_io.py export > logs/export.log 2>&1; grep -a protegidas logs/export.log
java -Djava.awt.headless=true -jar "$JAR" -de pikocore_gamepad.dsn -do pikocore_gamepad.ses -mp 60 -mt 1 -l en > logs/freerouting.log 2>&1 || true
"$KIPY" route_io.py import > logs/import.log 2>&1; grep -a "SES import" logs/import.log
"$KIPY" finish_pcb.py > logs/finish.log 2>&1; grep -a "guardado" logs/finish.log
drc; N1=$(abiertas); echo "pasada 1: $N1 abiertas"
cp pikocore_gamepad.kicad_pcb logs/pass1.kicad_pcb; cp logs/drc.json logs/drc_pass1.json
if [ "$N1" -eq 0 ]; then python ../../../.claude/skills/pcb-verify/scripts/read_drc.py logs/drc.json; echo "== CICLO DONE"; exit 0; fi
"$KIPY" route_io.py repaso > logs/repaso.log 2>&1; grep -a protegidas logs/repaso.log
java -Djava.awt.headless=true -jar "$JAR" -de pikocore_gamepad.dsn -do pikocore_gamepad.ses -mp 30 -mt 1 -l en > logs/freerouting2.log 2>&1 || true
"$KIPY" route_io.py import > /dev/null 2>&1; "$KIPY" finish_pcb.py > /dev/null 2>&1
drc; N2=$(abiertas); echo "pasada 2: $N2 abiertas"
if [ "$N2" -ge "$N1" ]; then cp logs/pass1.kicad_pcb pikocore_gamepad.kicad_pcb; cp logs/drc_pass1.json logs/drc.json; echo "pasada 2 descartada"; fi
python ../../../.claude/skills/pcb-verify/scripts/read_drc.py logs/drc.json || true
echo "== CICLO DONE"
