#!/usr/bin/env python3
"""Revisa el placement antes de rutear: solapamientos y piezas fuera de placa.

No reemplaza al DRC — lo precede. El DRC necesita la placa ruteada y tarda;
esto corre en un segundo sobre el board recien generado y dice si el layout
es viable, que es lo que hace falta mientras se itera con el DXF de Rhino.

Compara PAD CONTRA PAD, no bounding box contra bounding box. La diferencia
importa: el modulo de pantalla (J4) tapa 27.78 x 39.22 del frente pero su
cobre es solo la fila de 7 pines — y bajo el, en el dorso, conviene poner
componentes. Con comparacion por bbox, cada pieza del dorso bajo la pantalla
apareceria como choque.

Un par de pads se considera conflictivo si comparten capa de cobre, o si
alguno de los dos es pasante: un THT perfora las cuatro capas.

No mira courtyards: dos piezas cuyos courtyards se rozan suelen ser
aceptables, y aca lo que interesa es el cobre encimado. La excepcion es el
cuerpo de la pantalla (su F.CrtYd): ahi no puede asomar ninguna pata pasante,
ni pads SMD del frente ni courtyards del frente.

Correr con el python de KiCad:
  "$LOCALAPPDATA/Programs/KiCad/9.0/bin/python.exe" checks/check_placement.py
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_DIR = os.path.dirname(HERE)
sys.path.insert(0, PCB_DIR)
PCB = os.path.join(PCB_DIR, "pikocore_gamepad.kicad_pcb")

MARGEN_BORDE = 1.0    # mm minimos entre cobre y borde de placa

from placements import MODULE_BOX   # noqa: E402  (el modulo apoya plano)


def caja_pad(p):
    """Bounding box del pad, en mm."""
    b = p.GetBoundingBox()
    t = pcbnew.ToMM
    return (t(b.GetLeft()), t(b.GetTop()), t(b.GetRight()), t(b.GetBottom()))


def pads_de(fp):
    """[(ref.num, caja, pasante, cara)] de cada pad, en mm."""
    out = []
    for p in fp.Pads():
        pasante = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH,
                                       pcbnew.PAD_ATTRIB_NPTH)
        out.append((f"{fp.GetReference()}.{p.GetNumber() or '-'}",
                    caja_pad(p), pasante, fp.IsFlipped()))
    return out


def footprint_bbox(fp):
    cajas = [c for _, c, _, _ in pads_de(fp)]
    if not cajas:
        return None
    return (min(c[0] for c in cajas), min(c[1] for c in cajas),
            max(c[2] for c in cajas), max(c[3] for c in cajas))


def solapan(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def main(board=None):
    """rc 0 si el placement es viable. `board` permite probarlo en memoria."""
    if board is None:
        if not os.path.isfile(PCB):
            print(f"FALTA: {PCB}")
            return 1
        board = pcbnew.LoadBoard(PCB)
    bb = board.GetBoardEdgesBoundingBox()
    anchos = [d.GetWidth() for d in board.GetDrawings()
              if d.GetLayer() == pcbnew.Edge_Cuts]
    bb.Inflate(-(max(anchos) if anchos else 0) // 2)
    bx0, by0 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())
    bx1, by1 = pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())

    piezas, pads = [], []
    for fp in board.GetFootprints():
        caja = footprint_bbox(fp)
        if caja is None:
            continue
        piezas.append((fp.GetReference(), caja))
        pads.extend(pads_de(fp))
    piezas.sort()

    fuera = []
    for ref, c in piezas:
        if (c[0] < bx0 + MARGEN_BORDE or c[1] < by0 + MARGEN_BORDE or
                c[2] > bx1 - MARGEN_BORDE or c[3] > by1 - MARGEN_BORDE):
            fuera.append((ref, c))

    choques = []
    for i, (na, ca, pa, fa) in enumerate(pads):
        refa = na.split(".")[0]
        for nb, cb, pb, fb in pads[i + 1:]:
            if nb.split(".")[0] == refa:
                continue                      # pads del mismo componente
            if not solapan(ca, cb):
                continue
            if fa != fb and not (pa or pb):
                continue                      # caras opuestas, todo SMD
            cara = "misma cara" if fa == fb else "caras opuestas, hay pasante"
            choques.append((na, nb, cara))

    # El modulo va soldado plano al dorso: una cola pasante del frente
    # debajo de el lo levanta (o lo cortocircuita contra su cara inferior).
    mx0, my0, mx1, my1 = MODULE_BOX
    bajo_modulo = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            x, y = pcbnew.ToMM(p.GetX()), pcbnew.ToMM(p.GetY())
            if (p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
                    and mx0 < x < mx1 and my0 < y < my1):
                bajo_modulo.append(f"{fp.GetReference()}.{p.GetNumber()}")

    # La pantalla (J4) apoya en el frente sobre su header: ninguna pata pasante
    # de otra pieza (ni su soldadura, que queda en el frente) bajo su placa.
    # Los jacks del dorso sueldan sus patas del lado del frente. Tampoco una
    # pieza SMD del frente (pad o courtyard): el cuerpo del modulo la pisa.
    j4 = board.FindFootprintByReference("J4")
    if not j4:
        print("FALTA J4 (la pantalla): no se puede revisar que quede libre bajo ella.")
        return 1
    t = pcbnew.ToMM

    def caja_crtyd(fp):
        fp.BuildCourtyardCaches()
        poly = fp.GetCourtyard(pcbnew.F_CrtYd)
        if poly.OutlineCount() == 0:
            return None
        b = poly.BBox()
        return (t(b.GetLeft()), t(b.GetTop()), t(b.GetRight()), t(b.GetBottom()))

    cuerpo = caja_crtyd(j4)
    if cuerpo is None:
        print("J4 sin F.CrtYd: no se puede revisar que quede libre bajo la pantalla.")
        return 1
    bajo_pantalla = [n for n, c, pasante, _ in pads
                     if pasante and not n.startswith("J4.") and solapan(c, cuerpo)]
    # Courtyard por caja: conservador si alguno no es rectangular.
    smd_bajo_pantalla = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref == "J4":
            continue
        pad_f = any(p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD
                    and p.IsOnLayer(pcbnew.F_Cu)
                    and solapan(caja_pad(p), cuerpo) for p in fp.Pads())
        cc = caja_crtyd(fp)
        if pad_f or (cc and solapan(cc, cuerpo)):
            smd_bajo_pantalla.append(ref)

    # Sus pastillas se sueldan a mano: una via que toca el cobre de una
    # chupa el estano. Circulo de la via contra el rectangulo que envuelve la
    # pastilla: las pastillas son estadios, asi que la prueba es conservadora
    # (puede marcar una via junto a una esquina redondeada que no la toca).
    via_en_modulo = []
    u1 = board.FindFootprintByReference("U1")
    for v in board.GetTracks():
        if v.GetClass() != "PCB_VIA":
            continue
        r = v.GetWidth(pcbnew.F_Cu) / 2
        vx, vy = v.GetPosition().x, v.GetPosition().y
        for p in (u1.Pads() if u1 else []):
            if not p.GetNumber():
                continue
            c = p.GetBoundingBox()
            dx = max(c.GetLeft() - vx, 0, vx - c.GetRight())
            dy = max(c.GetTop() - vy, 0, vy - c.GetBottom())
            if dx * dx + dy * dy < r * r:
                via_en_modulo.append(f"U1.{p.GetNumber()} [{v.GetNetname()}]")

    print(f"{len(piezas)} piezas, {len(pads)} pads. "
          f"Placa {bx1 - bx0:.2f} x {by1 - by0:.2f} mm.\n")

    if fuera:
        print(f"FUERA DE PLACA o a menos de {MARGEN_BORDE}mm del borde ({len(fuera)}):")
        for ref, c in fuera:
            print(f"  {ref:<5}  x {c[0]:7.2f}..{c[2]:7.2f}   y {c[1]:7.2f}..{c[3]:7.2f}")
        print()
    if choques:
        print(f"PADS SOLAPADOS ({len(choques)}):")
        for na, nb, cara in choques[:20]:
            print(f"  {na:<8} vs {nb:<8}  ({cara})")
        if len(choques) > 20:
            print(f"  ... y {len(choques) - 20} mas")
        print()

    for n in bajo_modulo:
        print(f"TACTO BAJO EL MODULO: {n}")
    if bajo_modulo:
        print()

    for n in bajo_pantalla:
        print(f"PATA BAJO LA PANTALLA: {n}")
    if bajo_pantalla:
        print()

    for ref in smd_bajo_pantalla:
        print(f"BAJO LA PANTALLA: {ref}")
    if smd_bajo_pantalla:
        print()

    for n in via_en_modulo:
        print(f"VIA EN PASTILLA DEL MODULO: {n}")
    if via_en_modulo:
        print()

    if not (fuera or choques or bajo_modulo or bajo_pantalla
            or smd_bajo_pantalla or via_en_modulo):
        print("OK: sin solapamientos de pads y todo dentro de la placa.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
