#!/usr/bin/env python3
"""Export DSN / import SES para freerouting. Correr con el python de KiCad.

  "$KIPY" route_io.py export   -> pikocore_gamepad.dsn
  "$KIPY" route_io.py import   -> aplica pikocore_gamepad.ses, rellena zonas, guarda
  "$KIPY" route_io.py repaso   -> DSN de la placa YA ruteada, para completar
                                  lo que freerouting dejo sin conectar

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
import json
import os
import re
import sys

import pcbnew

# KiCad 9.0.1: ExportSpecctraDSN dispara un assert benigno de wxWidgets
# ("non-closed outline added to SHAPE_POLY_SET") y en vez de solo escribirlo
# por stderr abre un "wxWidgets Debug Alert" MODAL que nadie puede cerrar en
# CLI: el script queda colgado (paso tres veces el 2026-10-15, en export y
# en repaso). wxPython comparte la wx de KiCad: apagar los asserts aca apaga
# el dialogo para todo el proceso.
try:
    import wx
    wx.DisableAsserts()
except Exception:          # sin wxPython el assert sigue saliendo por stderr
    pass

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


# Foto del cobre previo al ruteo (nucleo RP2350A, manual_tracks.py,
# plane_vias.py). La escribe "export"; la lee "repaso".
PRE = os.path.join(HERE, "logs", "pre_ruteo.json")


def _clave(t):
    """Identidad geometrica de una pista o via, en micrones."""
    um = lambda v: int(round(v / 1000))
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition()
        return f"V {t.GetNetname()} {um(p.x)} {um(p.y)}"
    a, b = sorted([(um(t.GetStart().x), um(t.GetStart().y)),
                   (um(t.GetEnd().x), um(t.GetEnd().y))])
    return f"T {t.GetNetname()} {t.GetLayer()} {a} {b}"


def fijar_cableado(board, solo=None):
    """Bloquea pistas y vias para que el DSN las lleve como (type fix).

    Lo que llega al DSN antes de freerouting es deliberado: el nucleo del
    RP2350A copiado de la placa oficial, las pistas de manual_tracks.py y los
    fanouts de plane_vias.py. Como (type route) freerouting lo trata como
    propio y lo reacomoda: en la primera corrida del chip-down partio las
    pistas de 1V1 del regulador en dos islas. KiCad exporta lo bloqueado como
    (type fix); main() lo pasa a (type protect), que freerouting tampoco toca
    y que, a diferencia de fix, si devuelve en el SES.

    solo=None bloquea todo (export) y devuelve las claves para la foto. Con
    solo=claves bloquea unicamente eso (repaso): el SES no trae el bloqueo de
    vuelta, asi que se reconoce por geometria. Lo que puso freerouting queda
    como (type route) y en el repaso lo puede rehacer para hacer lugar.

    """
    claves = []
    for t in board.GetTracks():
        k = _clave(t)
        if solo is None or k in solo:
            t.SetLocked(True)
            claves.append(k)
    return claves


def blindar_zonas_externas(dsn_path):
    """Copia cada zona de F.Cu/B.Cu como keepout, solo para freerouting.

    Las zonas del nucleo RP2350A son anillos en la cara del chip: 3V3 por
    fuera, 1V1 por dentro, el pad expuesto GND al centro. El anillo de 1V1 es
    el que lleva la salida del regulador a los cuatro pines DVDD. freerouting
    no trata una zona (plane) ajena como obstaculo: en la segunda corrida paso
    SWCLK, DPAD_UP y otras cinco por adentro y partio el 1V1 en dos.

    Los pines de U1 quedan fuera del anillo de 3V3, asi que siguen
    accesibles. Las capas internas (GND, PWR) no se tocan: son los planos.
    Devuelve cuantos keepouts agrego.
    """
    import re
    with open(dsn_path, encoding="utf-8") as f:
        txt = f.read()
    pat = re.compile(r"\(plane \S+ \(polygon ([FB]\.Cu) 0 ([^)]*)\)\)")
    nuevos = [f'    (keepout "" (polygon {m.group(1)} 0 {m.group(2)}))'
              for m in pat.finditer(txt)]
    if nuevos:
        ult = list(pat.finditer(txt))[-1]
        txt = txt[:ult.end()] + "\n" + "\n".join(nuevos) + txt[ult.end():]
        with open(dsn_path, "w", encoding="utf-8") as f:
            f.write(txt)
    return len(nuevos)


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
        # Desde que gen_pcb.py pone la libreria en el FPID, KiCad exporta la
        # imagen como "Package_TO_SOT_SMD:SOT-563" (y si no la pone, como
        # "SOT-563" a secas). Se aceptan las dos formas.
        m = re.search(r'\(image "(?:[^"]*:)?%s"' % re.escape(nombre), txt)
        if not m:
            continue
        marca = m.group(0)
        i = m.start()
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
    if len(sys.argv) < 2 or sys.argv[1] not in ("export", "import", "repaso"):
        print(__doc__)
        return 2

    board = pcbnew.LoadBoard(PCB)

    if sys.argv[1] in ("export", "repaso"):
        if sys.argv[1] == "export":
            fijas = fijar_cableado(board)
            os.makedirs(os.path.dirname(PRE), exist_ok=True)
            with open(PRE, "w", encoding="utf-8") as f:
                json.dump(fijas, f)
        else:
            if not os.path.isfile(PRE):
                print(f"FALTA: {PRE} (correr export antes de rutear)")
                return 1
            with open(PRE, encoding="utf-8") as f:
                fijas = fijar_cableado(board, set(json.load(f)))
        # Solo en memoria: la placa no se guarda bloqueada.
        ok = pcbnew.ExportSpecctraDSN(board, DSN)
        zonas = len([z for z in board.Zones() if not z.GetIsRuleArea()])
        print(f"DSN export: {ok} -> {DSN}")
        print(f"{zonas} zonas conservadas (4 capas: el plano GND no se toca)")
        if ok:
            n = marcar_planos(DSN)
            print(f"{n} capa(s) interna(s) marcadas como (type power)")
            z = blindar_zonas_externas(DSN)
            print(f"{z} zona(s) de F.Cu/B.Cu copiadas como keepout")
            # (type fix) no vuelve en el SES de freerouting: el import borraba
            # el nucleo entero (182 conexiones abiertas). (type protect) si
            # vuelve, y freerouting tampoco lo mueve.
            with open(DSN, encoding="utf-8") as f:
                txt = f.read()
            with open(DSN, "w", encoding="utf-8") as f:
                f.write(txt.replace("(type fix)", "(type protect)"))
            print(f"{len(fijas)} pista(s)/via(s) previas protegidas")
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
    # El SES trae el diametro de la via pero no el taladro: KiCad le pone el
    # de la netclass. Una via de 0.45 (la de senal) en una net Power salia con
    # taladro 0.3, anillo 0.075 (minimo 0.1). Se baja el taladro hasta dejar
    # anillo de 0.125.
    arregladas = 0
    for v in board.GetTracks():
        if v.GetClass() != "PCB_VIA":
            continue
        d = v.GetWidth(pcbnew.F_Cu)
        if (d - v.GetDrillValue()) / 2 < pcbnew.FromMM(0.1):
            v.SetDrill(d - pcbnew.FromMM(0.25))
            arregladas += 1
    if arregladas:
        print(f"vias con anillo corto: taladro corregido en {arregladas}")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)
    pistas = len([t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"])
    vias = len([t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"])
    print(f"guardado: {PCB}  ({pistas} pistas, {vias} vias)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
