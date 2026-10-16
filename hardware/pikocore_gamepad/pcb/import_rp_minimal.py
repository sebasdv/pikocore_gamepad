#!/usr/bin/env python3
"""Importa el NUCLEO del RP2350A desde la placa minima oficial de Raspberry Pi.

Correr UNA vez, con el python de KiCad 10 (el archivo oficial esta en formato
de KiCad 10 y el 9 no lo lee):

  "C:/Program Files/KiCad/10.0/bin/python.exe" import_rp_minimal.py <zip>

<zip> = "RP-010328-CA-1-RP2350A Minimal KiCAD.zip", de
https://pip.raspberrypi.com/categories/1214-rp2350 (licencia MIT, ver el
LICENSE.txt del zip). Lo que escribe queda versionado y el pipeline normal
(KiCad 9) no necesita ni el zip ni KiCad 10:

  lib/rp_minimal.pretty/*.kicad_mod   las huellas usadas por el nucleo, en
                                      formato que KiCad 9 lee
  rp_core_ref.py                      posiciones de las piezas, pistas, vias
                                      y zonas del nucleo RELATIVAS a U1, en
                                      el marco de la placa oficial (frente)

POR QUE COPIAR Y NO DIBUJAR: "Hardware design with RP2350" (RP-008280-DS)
seccion 2.1 sobre el regulador interno: "if you choose not to use our
example, then you do so at your own risk". El layout del regulador (L1, C6,
C7, C9, R3 y las zonas de 1V1 / VREG_LX) es lo que hace que el RP2350 de
1.1V estable bajo carga, y la guia dice que se llego a el con muchas
iteraciones. Lo mismo para el cristal (seccion 4). Este script copia esa
geometria numero por numero.
"""
import os
import re
import sys
import zipfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "lib", "rp_minimal.pretty")
OUT_PY = os.path.join(HERE, "rp_core_ref.py")
mm = pcbnew.ToMM

# Piezas del nucleo que se copian. Quedan afuera, a proposito:
#   R1  (pull-up de QSPI_SS, DNF en la placa oficial)
#   R9  (0R opcional para un segundo chip de memoria en GPIO0)
#   SW1/SW2/R4 (botones: se colocan aparte, donde la placa tiene lugar)
#   J1/J2/J3/J4/U2/C1/C5/C19 (USB micro, headers, LDO: esta placa tiene los
#   suyos)
CORE = ["U1", "L1", "C6", "C7", "C9", "R3", "C8", "C10", "C11", "C12", "C13",
        "C14", "C15", "C16", "C17", "C18", "X1", "C3", "C4", "R2", "R7", "R8",
        "U3", "C2", "R6", "R10"]

# Nets cuyo cobre se copia ENTERO (son locales al nucleo).
NETS_LOCALES = {"+1V1", "/VREG_LX", "/VREG_AVDD", "/XIN", "/XOUT",
                "Net-(C4-Pad1)", "/QSPI_SD0", "/QSPI_SD1", "/QSPI_SD2",
                "/QSPI_SD3", "/QSPI_SCLK", "/QSPI_SS", "/FLASH_SS",
                "Net-(U1-USB_DP)", "Net-(U1-USB_DM)"}
# Nets globales: solo el cobre que cae entero dentro del nucleo (los tramos
# entre un capacitor y su pin). El resto llega por los planos de esta placa.
NETS_GLOBALES = {"+3V3", "GND"}
CAJA = (-9.0, -19.5, 9.5, 14.5)     # dx0, dy0, dx1, dy1 alrededor de U1
# Area del bbox. Las del nucleo van de 0.6 a 43 mm2 (el anillo de 3V3 bajo
# el chip mide 5.6 x 5.6 y la isla de GND del cristal 6.4 x 6.7); los
# vertidos de placa entera de la oficial miden 955 y 2175. 60 separa limpio.
ZONA_MAX_MM2 = 60.0

# Fanout de los GPIO: la placa oficial los saca por la cara del chip, en
# linea recta entre los capacitores de desacoplo, sin vias. freerouting no
# encuentra esa salida (paso 0.4: planta una via en la punta de un pad y tapa
# a los vecinos) y en cada corrida quedaban dos o tres GPIO abiertos. Se copia
# el tramo hasta FANOUT_R mm del centro de U1; ahi queda un extremo libre y
# freerouting sigue desde el.
NETS_FANOUT = re.compile(r"^/(GPIO\d+(_ADC\d)?|RUN|SWD|SWCLK)$")
FANOUT_R = 12.5  # hasta el final real de los carriles de RP (8.8..12): extremos escalonados, con lugar para una via en cada punta


def recortar(xa, ya, xb, yb, r=FANOUT_R):
    """Segmento recortado al cuadrado |x|,|y| <= r (Liang-Barsky), o None."""
    t0, t1 = 0.0, 1.0
    dx, dy = xb - xa, yb - ya
    for p, q in ((-dx, xa + r), (dx, r - xa), (-dy, ya + r), (dy, r - ya)):
        if p == 0:
            if q < 0:
                return None
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
    if t0 > t1:
        return None
    return (xa + t0 * dx, ya + t0 * dy, xa + t1 * dx, ya + t1 * dy)


def dentro(x, y):
    return CAJA[0] <= x <= CAJA[2] and CAJA[1] <= y <= CAJA[3]


def F(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


# --------------------------------------------------------------- huellas
PAD_ATTR = {0: "thru_hole", 1: "smd", 2: "connect", 3: "np_thru_hole"}
PAD_SHAPE = {0: "circle", 1: "rect", 2: "oval", 4: "roundrect"}


# KiCad 10 devuelve los nombres LARGOS de capa ("F.Courtyard",
# "F.Silkscreen"). En un .kicad_mod KiCad 9 solo entiende los canonicos; con
# los largos manda la figura a una capa "Rescue" que despues escribe en la
# placa y NO puede volver a leer: la placa guardada no abre mas.
CANONICAS = {"F.Courtyard": "F.CrtYd", "B.Courtyard": "B.CrtYd",
             "F.Silkscreen": "F.SilkS", "B.Silkscreen": "B.SilkS",
             "F.Adhesive": "F.Adhes", "B.Adhesive": "B.Adhes"}


def capa(board, lid):
    n = board.GetLayerName(lid)
    return CANONICAS.get(n, n)


def fp_texto(board, fp_orig):
    fp = pcbnew.FOOTPRINT(fp_orig)
    fp.SetOrientationDegrees(0)
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    name = fp.GetFPID().GetLibItemName().wx_str()
    out = [f'(footprint "{name}"\n', '  (version 20240108)\n',
           '  (generator "import_rp_minimal.py")\n', '  (layer "F.Cu")\n',
           '  (attr smd)\n',
           f'  (descr "Copiada de RPI-RP2350A-MINIMAL_R4-S1 (Raspberry Pi, '
           f'MIT) por import_rp_minimal.py. No editar a mano.")\n',
           '  (property "Reference" "REF**" (at 0 -1.5 0) (layer "F.SilkS") '
           '(effects (font (size 0.6 0.6) (thickness 0.1))))\n',
           f'  (property "Value" "{name}" (at 0 1.5 0) (layer "F.Fab") '
           '(effects (font (size 0.6 0.6) (thickness 0.1))))\n']
    for p in fp.Pads():
        L = pcbnew.F_Cu
        attr = PAD_ATTR[p.GetAttribute()]
        shape = PAD_SHAPE.get(p.GetShape(L), "rect")
        pos, sz = p.GetPosition(), p.GetSize(L)
        rot = p.GetOrientationDegrees()
        if attr == "thru_hole":
            layers = '"*.Cu"'
            drill = f' (drill {F(mm(p.GetDrillSize().x))})'
        else:
            layers = " ".join(f'"{capa(board, l)}"'
                              for l in p.GetLayerSet().Seq())
            drill = ""
        extra = (f' (roundrect_rratio {F(p.GetRoundRectRadiusRatio(L))})'
                 if shape == "roundrect" else "")
        out.append(f'  (pad "{p.GetNumber()}" {attr} {shape} '
                   f'(at {F(mm(pos.x))} {F(mm(pos.y))} {F(rot)}) '
                   f'(size {F(mm(sz.x))} {F(mm(sz.y))}){drill} '
                   f'(layers {layers}){extra})\n')
    for g in fp.GraphicalItems():
        if g.GetClass() != "PCB_SHAPE":
            continue
        ln = capa(board, g.GetLayer())
        w = F(mm(g.GetWidth()))
        fill = "yes" if g.IsSolidFill() else "no"    # KiCad 10: no IsFilled
        st = g.GetShape()
        if st == pcbnew.SHAPE_T_SEGMENT:
            a, b = g.GetStart(), g.GetEnd()
            out.append(f'  (fp_line (start {F(mm(a.x))} {F(mm(a.y))}) '
                       f'(end {F(mm(b.x))} {F(mm(b.y))}) '
                       f'(stroke (width {w}) (type solid)) (layer "{ln}"))\n')
        elif st == pcbnew.SHAPE_T_RECTANGLE:
            a, b = g.GetStart(), g.GetEnd()
            out.append(f'  (fp_rect (start {F(mm(a.x))} {F(mm(a.y))}) '
                       f'(end {F(mm(b.x))} {F(mm(b.y))}) '
                       f'(stroke (width {w}) (type solid)) (fill {fill}) '
                       f'(layer "{ln}"))\n')
        elif st == pcbnew.SHAPE_T_CIRCLE:
            c, e = g.GetCenter(), g.GetEnd()
            out.append(f'  (fp_circle (center {F(mm(c.x))} {F(mm(c.y))}) '
                       f'(end {F(mm(e.x))} {F(mm(e.y))}) '
                       f'(stroke (width {w}) (type solid)) (fill {fill}) '
                       f'(layer "{ln}"))\n')
        elif st == pcbnew.SHAPE_T_ARC:
            a, m, b = g.GetStart(), g.GetArcMid(), g.GetEnd()
            out.append(f'  (fp_arc (start {F(mm(a.x))} {F(mm(a.y))}) '
                       f'(mid {F(mm(m.x))} {F(mm(m.y))}) '
                       f'(end {F(mm(b.x))} {F(mm(b.y))}) '
                       f'(stroke (width {w}) (type solid)) (layer "{ln}"))\n')
        elif st == pcbnew.SHAPE_T_POLY:
            ol = g.GetPolyShape().Outline(0)
            pts = " ".join(f"(xy {F(mm(ol.CPoint(i).x))} "
                           f"{F(mm(ol.CPoint(i).y))})"
                           for i in range(ol.PointCount()))
            out.append(f'  (fp_poly (pts {pts}) '
                       f'(stroke (width {w}) (type solid)) (fill {fill}) '
                       f'(layer "{ln}"))\n')
    out.append(')\n')
    return name, "".join(out)


# ------------------------------------------------------------------ cobre
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    z = zipfile.ZipFile(sys.argv[1])
    pcb_name = next(n for n in z.namelist() if n.endswith(".kicad_pcb"))
    tmp = os.path.join(os.environ.get("TEMP", HERE), "rp_minimal_import")
    os.makedirs(tmp, exist_ok=True)
    pcb = os.path.join(tmp, os.path.basename(pcb_name))
    with open(pcb, "wb") as f:
        f.write(z.read(pcb_name))
    board = pcbnew.LoadBoard(pcb)
    u1 = board.FindFootprintByReference("U1")
    ox, oy = mm(u1.GetPosition().x), mm(u1.GetPosition().y)
    assert u1.GetOrientationDegrees() == 0 and not u1.IsFlipped()

    os.makedirs(LIB, exist_ok=True)
    parts, escritas = {}, set()
    for ref in CORE:
        fp = board.FindFootprintByReference(ref)
        name, txt = fp_texto(board, fp)
        if name not in escritas:
            with open(os.path.join(LIB, name + ".kicad_mod"), "w",
                      encoding="utf-8") as f:
                f.write(txt)
            escritas.add(name)
        parts[ref] = (name, round(mm(fp.GetPosition().x) - ox, 4),
                      round(mm(fp.GetPosition().y) - oy, 4),
                      round(fp.GetOrientationDegrees(), 3), fp.GetValue())

    tracks, vias = [], []
    for t in board.GetTracks():
        net = t.GetNetname()
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            x, y = mm(p.x) - ox, mm(p.y) - oy
            if net in NETS_LOCALES or (net in NETS_GLOBALES and dentro(x, y)):
                vias.append((net, round(x, 4), round(y, 4),
                             round(mm(t.GetWidth(pcbnew.F_Cu)), 4),
                             round(mm(t.GetDrillValue()), 4)))
            continue
        if t.GetClass() != "PCB_TRACK":
            continue
        a, b = t.GetStart(), t.GetEnd()
        xa, ya, xb, yb = mm(a.x) - ox, mm(a.y) - oy, mm(b.x) - ox, mm(b.y) - oy
        if net in NETS_LOCALES or (net in NETS_GLOBALES and dentro(xa, ya)
                                   and dentro(xb, yb)):
            tracks.append((net, board.GetLayerName(t.GetLayer()),
                           round(xa, 4), round(ya, 4), round(xb, 4),
                           round(yb, 4), round(mm(t.GetWidth()), 4)))

    fanout = []
    for t in board.GetTracks():
        if t.GetClass() != "PCB_TRACK" or not NETS_FANOUT.match(t.GetNetname()):
            continue
        a, b = t.GetStart(), t.GetEnd()
        seg = recortar(mm(a.x) - ox, mm(a.y) - oy, mm(b.x) - ox, mm(b.y) - oy)
        if seg is None or (abs(seg[0] - seg[2]) < 1e-6
                           and abs(seg[1] - seg[3]) < 1e-6):
            continue
        fanout.append((t.GetNetname(), board.GetLayerName(t.GetLayer()))
                      + tuple(round(v, 4) for v in seg)
                      + (round(mm(t.GetWidth()), 4),))

    zones = []
    for zn in board.Zones():
        if zn.GetIsRuleArea():
            continue
        bb = zn.GetBoundingBox()
        area = mm(bb.GetWidth()) * mm(bb.GetHeight())
        cx = mm(bb.Centre().x) - ox
        cy = mm(bb.Centre().y) - oy
        if area > ZONA_MAX_MM2 or not dentro(cx, cy):
            continue
        ol = zn.Outline().Outline(0)
        pts = [(round(mm(ol.CPoint(i).x) - ox, 4),
                round(mm(ol.CPoint(i).y) - oy, 4))
               for i in range(ol.PointCount())]
        zones.append(dict(
            net=zn.GetNetname(),
            layer=board.GetLayerName(zn.GetLayerSet().Seq()[0]),
            pts=pts, priority=zn.GetAssignedPriority(),
            clearance=round(mm(zn.GetLocalClearance() or 0), 4),
            min_thickness=round(mm(zn.GetMinThickness()), 4),
            connection=int(zn.GetPadConnection()),
            thermal_gap=round(mm(zn.GetThermalReliefGap()), 4),
            spoke=round(mm(zn.GetThermalReliefSpokeWidth()), 4)))

    with open(OUT_PY, "w", encoding="utf-8") as f:
        f.write('"""Nucleo del RP2350A copiado de la placa minima oficial de '
                'Raspberry Pi\n(RPI-RP2350A-MINIMAL_R4-S1, licencia MIT). '
                'GENERADO por import_rp_minimal.py:\nno editar a mano.\n\n'
                'Coordenadas en mm RELATIVAS a U1, en el marco de la placa '
                'oficial: vista\nde frente, Y hacia abajo, piezas en F.Cu. '
                'rp_core.py las lleva a esta placa\n(dorso, rotadas y '
                'trasladadas) con operaciones de pcbnew, no a mano.\n"""\n\n')
        f.write("# ref oficial -> (huella en rp_minimal, dx, dy, rot, valor)\n")
        f.write("PARTS = {\n")
        for ref in CORE:
            f.write(f"    {ref!r}: {parts[ref]!r},\n")
        f.write("}\n\n# (net, capa, x0, y0, x1, y1, ancho)\nTRACKS = [\n")
        for t in tracks:
            f.write(f"    {t!r},\n")
        f.write("]\n\n# (net, x, y, diametro, taladro)\nVIAS = [\n")
        for v in vias:
            f.write(f"    {v!r},\n")
        f.write("]\n\n# Fanout de GPIO/RUN/SWD hasta FANOUT_R del centro, nets de la\n"
                "# placa oficial (rp_core.py las traduce con pinmap.GPIO).\n"
                "# (net, capa, x0, y0, x1, y1, ancho)\nFANOUT = [\n")
        for t in fanout:
            f.write(f"    {t!r},\n")
        f.write("]\n\nZONES = [\n")
        for zn in zones:
            f.write(f"    {zn!r},\n")
        f.write("]\n")
    print(f"huellas: {sorted(escritas)}")
    print(f"piezas {len(parts)}, pistas {len(tracks)}, vias {len(vias)}, "
          f"zonas {len(zones)}, fanout {len(fanout)} -> {OUT_PY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
