#!/usr/bin/env python3
"""Export DSN / import SES para freerouting. Correr con el python de KiCad.

  "$KIPY" route_io.py export   -> pikocore_gamepad.dsn
  "$KIPY" route_io.py import   -> aplica pikocore_gamepad.ses, rellena zonas, guarda

DIFERENCIA CON V1: alli habia que QUITAR las zonas GND antes de exportar, para
que freerouting ruteara GND como pistas. Eso era un parche a la fragmentacion
del plano en 2 capas: con tanto THT el plano quedaba partido en islas y no
habia forma de garantizar conectividad de tierra por relleno.

Con 4 capas In1.Cu es un plano GND continuo, asi que las zonas se CONSERVAN en
el export y freerouting solo tiene que rutear las senales, conectando cada pad
GND al plano por via.

PITFALL heredado de V1: NO pasar este script ni kicad-cli por "2>&1 | grep".
El assert de "non-closed outline" mas el memory-leak de SWIG salen por stderr
y hacen deadlock del pipe — parece colgado. Redirigir a un log y grepear el
archivo.
"""
import os
import re
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "pikocore_gamepad.kicad_pcb")
DSN = os.path.join(HERE, "pikocore_gamepad.dsn")
SES = os.path.join(HERE, "pikocore_gamepad.ses")


# Capas internas que son PLANOS, no capas de senal.
PLANOS = ("GND", "PWR")


def marcar_planos(dsn_path):
    """Reescribe (type signal) -> (type power) en las capas de PLANOS.

    POR QUE HACE FALTA: KiCad exporta las CUATRO capas como (type signal), sin
    importar que In1/In2 sean planos macizos llenos por zona. freerouting lee
    eso literalmente y rutea senales POR ENCIMA de los planos: en la primera
    corrida metio 90 pistas en GND y 80 en PWR (I2S_BCK, DPAD_*, BTN_*...),
    y cada una de esas pistas PARTE el plano por donde pasa.

    Eso rompe justamente la premisa que documenta el docstring de arriba —
    "con 4 capas In1.Cu es un plano GND continuo"— y ademas deja pads de GND
    sin conectar al plano, porque el relleno esquiva las pistas ajenas.

    Con (type power) freerouting trata la capa como plano: no rutea sobre
    ella, solo la usa como destino de vias. Devuelve cuantas capas cambio.
    """
    with open(dsn_path, encoding="utf-8") as f:
        txt = f.read()
    n = 0
    for capa in PLANOS:
        # (layer GND\n      (type signal)  ->  (type power)
        viejo = f"(layer {capa}\n      (type signal)"
        nuevo = f"(layer {capa}\n      (type power)"
        if viejo in txt:
            txt = txt.replace(viejo, nuevo, 1)
            n += 1
    if n:
        with open(dsn_path, "w", encoding="utf-8") as f:
            f.write(txt)
    return n


# Footprints cuyo contorno hay que quitar del DSN para poder rutearlos.
SIN_OUTLINE = ("SOT-563",)


def limpiar_outlines(dsn_path):
    """Borra las lineas (outline ...) de los footprints de SIN_OUTLINE.

    POR QUE: KiCad exporta al DSN la serigrafia y el courtyard de cada
    footprint como (outline ...), y freerouting las trata como OBSTACULOS.
    En un encapsulado normal da igual —el ruteo pasa lejos— pero el SOT-563
    mide 1.2x1.6mm y sus outlines en y=+-0.94 sellan el corredor que hay
    entre las dos columnas de pads.

    Ese corredor es justamente por donde TI dice que hay que rutear. De la
    guia de layout del TPS61023 (SLVAES4, seccion 4): "the SW pin is in the
    middle of the VOUT pin and GND pin, place the SW trace UNDERNEATH the
    device". Con 0.74mm libres entre columnas, una pista de 0.20 entra con
    clearance de sobra.

    Sin esto, los pines del MEDIO (2=GND y 5=VOUT) quedan inalcanzables: el
    paso de 0.50mm no deja meter una pista entre pads adyacentes (0.15mm de
    hueco contra los 0.60 que hacen falta), asi que el unico acceso es por
    abajo. Eran 4 de las 4 conexiones que el autorouter dejaba sin resolver.

    Se borra SOLO el contorno, no los pads: la geometria de cobre no cambia.
    """
    with open(dsn_path, encoding="utf-8") as f:
        txt = f.read()
    total = 0
    for nombre in SIN_OUTLINE:
        marca = f'(image "{nombre}"'
        i = txt.find(marca)
        if i < 0:
            continue
        # el bloque de la imagen termina donde empieza la siguiente
        j = txt.find('(image "', i + len(marca))
        if j < 0:
            j = len(txt)
        bloque = txt[i:j]
        patron = r"[ \t]*\(outline \(path [^\n]*\)\)\n"
        limpio, n = re.subn(patron, "", bloque)
        if n:
            txt = txt[:i] + limpio + txt[j:]
            total += n
    if total:
        with open(dsn_path, "w", encoding="utf-8") as f:
            f.write(txt)
    return total


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("export", "import"):
        print(__doc__)
        return 2

    board = pcbnew.LoadBoard(PCB)

    if sys.argv[1] == "export":
        ok = pcbnew.ExportSpecctraDSN(board, DSN)
        zonas = len([z for z in board.Zones() if not z.GetIsRuleArea()])
        print(f"DSN export: {ok} -> {DSN}")
        print(f"{zonas} zonas conservadas (4 capas: el plano GND no se toca)")
        if ok:
            n = marcar_planos(DSN)
            print(f"{n} capa(s) interna(s) marcadas como (type power)")
            k = limpiar_outlines(DSN)
            print(f"{k} outline(s) quitadas de {'/'.join(SIN_OUTLINE)} "
                  f"(dejan rutear por debajo del chip)")
        return 0 if ok else 1

    if not os.path.isfile(SES):
        print(f"FALTA: {SES} (correr freerouting primero)")
        return 1
    try:
        ok = pcbnew.ImportSpecctraSES(board, SES)
    except TypeError:
        ok = pcbnew.ImportSpecctraSES(SES)
    print("SES import:", ok)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)
    pistas = len([t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"])
    vias = len([t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"])
    print(f"guardado: {PCB}  ({pistas} pistas, {vias} vias)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
