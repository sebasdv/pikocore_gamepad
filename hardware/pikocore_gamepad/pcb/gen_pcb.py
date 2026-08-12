#!/usr/bin/env python3
"""Genera pikocore_gamepad.kicad_pcb: contorno, stack de 4 capas, colocacion y zonas.

Correr con el python de KiCad 9:
  "$LOCALAPPDATA/Programs/KiCad/9.0/bin/python.exe" gen_pcb.py

STACK DE 4 CAPAS — es la diferencia de fondo con V1:
  F.Cu    senales del frente y componentes de panel
  In1.Cu  GND SOLIDO, sin cortes
  In2.Cu  alimentacion (3V3 / VSYS / 5V en bandas separadas)
  B.Cu    senales del dorso y componentes

Con 2 capas y tanto THT, los taladros perforaban ambos planos y fragmentaban
GND en 15-28 islas. Eso NO se puede cerrar por codigo: ZONE_FILLER().Fill()
via scripting no elimina islas (si funciona en la GUI), y kicad-cli pcb drc
re-rellena las zonas internamente, ignorando cualquier edicion del relleno.
En V1 la salida fue rutear GND como pistas. Aca In1.Cu queda entera bajo la
seccion de audio y el DAC tiene plano de retorno continuo.

Los pasivos no estan en placements.py: se colocan en una grilla automatica
del dorso y el usuario los reubica en Rhino junto con el resto.
"""
import math
import os
import re

import pcbnew

from netlist import INSTANCES
from placements import PLACEMENTS, BOARD_W, BOARD_H, FREE_REGIONS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "pikocore_gamepad.kicad_pcb")
NET = os.path.join(HERE, "pikocore_gamepad.net")
W, H = BOARD_W, BOARD_H

CORNER_R = 3.0          # radio de las esquinas del contorno
EDGE_KEEPOUT = 0.6      # franja sin pistas/vias contra el borde
ZONE_MARGIN = 0.5       # retiro de las zonas respecto del contorno

# Ruta estandar de footprints de la instalacion.
_cands = [os.path.abspath(os.path.join(os.path.dirname(pcbnew.__file__),
                                       *([".."] * n), "share", "kicad", "footprints"))
          for n in (3, 4, 2)]
KICAD_SHARE = next(p for p in _cands if os.path.isdir(p))

PROJ_LIBS = {
    "gamesetup_lcsc": os.path.join(HERE, "lib", "gamesetup_lcsc.pretty"),
    "gamesetup_fp": os.path.join(HERE, "lib", "gamesetup_fp.pretty"),
}

# Separacion entre courtyards vecinos. 0.5mm alcanza porque el courtyard ya
# incluye el margen de ensamblado de la pieza; sumarle mas solo desperdicia
# area.
PASIVO_CLR = 0.5


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def rounded_rect_pts(x0, y0, x1, y1, R, n=8):
    """Poligono que aproxima un rectangulo de esquinas redondeadas.
    Coords KiCad (Y hacia abajo); angulos de pantalla: 0=der, 90=abajo."""
    pts = []
    for cx, cy, a0, a1 in [(x1 - R, y0 + R, 270, 360),
                           (x1 - R, y1 - R, 0, 90),
                           (x0 + R, y1 - R, 90, 180),
                           (x0 + R, y0 + R, 180, 270)]:
        for i in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * i / n)
            pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
    return pts


def load_netmap():
    """{(ref, pin): net} y el conjunto de nombres, leidos del .net exportado."""
    txt = open(NET, encoding="utf-8").read()
    seccion = txt.split("(nets", 1)[1]
    netmap, nombres = {}, set()
    for chunk in re.split(r"\(net ", seccion)[1:]:
        m = re.search(r'\(name "([^"]+)"\)', chunk)
        if not m:
            continue
        name = m.group(1)
        for ref, pin in re.findall(
                r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', chunk):
            netmap[(ref, pin)] = name
        nombres.add(name)
    return netmap, nombres


def find_fp(lib_id):
    lib, _, name = lib_id.partition(":")
    path = PROJ_LIBS.get(lib, os.path.join(KICAD_SHARE, lib + ".pretty"))
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise RuntimeError(f"No se pudo cargar {lib_id} desde {path}")
    return fp


def dibujar_contorno(board):
    R = CORNER_R
    s = math.sqrt(2) / 2
    for x1, y1, x2, y2 in [(R, 0, W - R, 0), (W, R, W, H - R),
                           (W - R, H, R, H), (0, H - R, 0, R)]:
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pt(x1, y1))
        seg.SetEnd(pt(x2, y2))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.1))
        board.Add(seg)
    for start, mid, end in [
            ((W - R, 0), (W - R + R * s, R - R * s), (W, R)),
            ((W, H - R), (W - R + R * s, H - R + R * s), (W - R, H)),
            ((R, H), (R - R * s, H - R + R * s), (0, H - R)),
            ((0, R), (R - R * s, R - R * s), (R, 0))]:
        arc = pcbnew.PCB_SHAPE(board)
        arc.SetShape(pcbnew.SHAPE_T_ARC)
        arc.SetArcGeometry(pt(*start), pt(*mid), pt(*end))
        arc.SetLayer(pcbnew.Edge_Cuts)
        arc.SetWidth(mm(0.1))
        board.Add(arc)


def setup_stackup(board):
    """4 capas. In1.Cu es GND solido; In2.Cu, alimentacion."""
    board.SetCopperLayerCount(4)
    board.SetLayerName(pcbnew.In1_Cu, "GND")
    board.SetLayerName(pcbnew.In2_Cu, "PWR")


def setup_netclasses(board):
    """Netclass Power a 0.4mm para los tres rieles.

    0.4 y no 0.5: el hueco entre pads del socket U1 es 0.84mm, y una pista de
    0.4 mas 2x0.2 de clearance da 0.8, que pasa justo. Con 0.5 serian 0.9 y no
    entra. El DSN lleva la clase y freerouting la respeta.
    """
    ns = board.GetDesignSettings().m_NetSettings
    nc = pcbnew.NETCLASS("Power")
    nc.SetTrackWidth(mm(0.4))
    ns.SetNetclass("Power", nc)
    for pn in ("3V3", "VSYS", "5V", "VSYS_F"):
        ns.SetNetclassPatternAssignment(pn, "Power")
    ns.RecomputeEffectiveNetclasses()


def _pad_bbox_mm(fp):
    xs0, ys0, xs1, ys1 = [], [], [], []
    for p in fp.Pads():
        b = p.GetBoundingBox()
        xs0.append(b.GetLeft()); ys0.append(b.GetTop())
        xs1.append(b.GetRight()); ys1.append(b.GetBottom())
    t = pcbnew.ToMM
    return (t(min(xs0)), t(min(ys0)), t(max(xs1)), t(max(ys1)))


def _ocupacion_mm(fp):
    """Caja que la pieza necesita para si: la UNION de su courtyard y sus pads.

    Hay que mirar los dos, y ninguno alcanza solo:

    - El courtyard no basta como unica referencia porque no siempre esta bien
      dimensionado. El DIP-8 importado de LCSC declara 8.9 x 6.5 cuando sus
      pads ocupan 9.42 x 9.42: fiarse del courtyard mete pasivos encima del
      op-amp, con el cobre superpuesto.

    - Los pads no bastan porque un electrolitico CP_Elec_6.3x5.4 mide 9.10 x
      1.60 entre pads pero su cuerpo ocupa 6.9 x 6.0. Empaquetar por pads los
      encima aunque el cobre no se toque, y el DRC lo reporta como
      courtyards_overlap: en una placa ensamblada por maquina, la pieza no
      entra.
    """
    caja = _pad_bbox_mm(fp)
    poly = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
    if poly and poly.OutlineCount() > 0:
        b, t = poly.BBox(), pcbnew.ToMM
        caja = (min(caja[0], t(b.GetLeft())), min(caja[1], t(b.GetTop())),
                max(caja[2], t(b.GetRight())), max(caja[3], t(b.GetBottom())))
    return caja


PASO_BUSQUEDA = 1.0     # mm: resolucion al buscar hueco


def _choca(caja, ocupadas):
    x0, y0, x1, y1 = caja
    for ox0, oy0, ox1, oy1 in ocupadas:
        if x0 < ox1 and ox0 < x1 and y0 < oy1 and oy0 < y1:
            return True
    return False


def _ocupadas_del_dorso(board):
    """Courtyards que bloquean el dorso: todo lo ya colocado que este al dorso
    o tenga pads pasantes, porque un THT perfora las cuatro capas."""
    out = []
    for fp in board.GetFootprints():
        pasante = any(p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH,
                                           pcbnew.PAD_ATTRIB_NPTH)
                      for p in fp.Pads())
        if fp.IsFlipped() or pasante:
            out.append(_ocupacion_mm(fp))
    return out


def empaquetar_pasivos(board, faltan):
    """Coloca en el dorso los componentes sin posicion manual.

    Busca hueco dentro de las regiones que declara placements.py, usando el
    COURTYARD de cada pieza y ESQUIVANDO todo lo que ya esta colocado. Las dos
    cosas importan:

    - Por courtyard y no por pads: un electrolitico mide 9.10 x 1.60 entre
      pads pero su courtyard es 6.9 x 6.0. Empaquetar por pads los encima
      aunque el cobre no se toque, y en una placa ensamblada por maquina eso
      significa que la pieza no entra.

    - Esquivando lo colocado: las regiones son una indicacion gruesa de donde
      hay lugar, no un area garantizada. Si el usuario mueve un control en
      Rhino y una region le queda encima, el empaquetador se corre solo en vez
      de apilar piezas.

    Se ordenan de mayor a menor: las grandes entran primero, cuando todavia
    hay huecos enteros.
    """
    piezas = []
    for ref, lib_id in faltan:
        fp = find_fp(lib_id)
        fp.SetReference(ref)
        board.Add(fp)
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        b = _ocupacion_mm(fp)
        piezas.append((b[2] - b[0], b[3] - b[1], fp))
    piezas.sort(key=lambda p: -(p[0] * p[1]))

    # Las recien agregadas estan todas en el origen: no cuentan como ocupadas
    # hasta que se ubiquen.
    ocupadas = [c for c in _ocupadas_del_dorso(board)
                if not (c[0] < 5 and c[1] < 5)]

    sin_lugar = []
    for w, h, fp in piezas:
        puesto = False
        for rx0, ry0, rx1, ry1 in FREE_REGIONS:
            cy = ry0
            while cy + h <= ry1 and not puesto:
                cx = rx0
                while cx + w <= rx1:
                    caja = (cx - PASIVO_CLR, cy - PASIVO_CLR,
                            cx + w + PASIVO_CLR, cy + h + PASIVO_CLR)
                    if not _choca(caja, ocupadas):
                        # El origen del footprint no es la esquina de su
                        # courtyard: se mueve por la diferencia.
                        b = _ocupacion_mm(fp)
                        pos = fp.GetPosition()
                        fp.SetPosition(pcbnew.VECTOR2I(
                            pos.x + mm(cx - b[0]), pos.y + mm(cy - b[1])))
                        ocupadas.append((cx, cy, cx + w, cy + h))
                        puesto = True
                        break
                    cx += PASO_BUSQUEDA
                cy += PASO_BUSQUEDA
            if puesto:
                break
        if not puesto:
            sin_lugar.append(fp.GetReference())
    return sin_lugar


def colocar(board, netmap, nets):
    """Footprints de placements.py, mas los pasivos en grilla automatica."""
    colocados = set()
    for ref, lib_id, x, y, rot, flip in PLACEMENTS:
        fp = find_fp(lib_id)
        fp.SetReference(ref)
        board.Add(fp)
        fp.SetPosition(pt(x, y))
        if flip:
            fp.Flip(pt(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
        colocados.add(ref)

    faltan = [(i[1], i[6]["FP"]) for i in INSTANCES if i[1] not in colocados]
    sin_lugar = empaquetar_pasivos(board, faltan)

    # Refdes a la capa Fab y valor a Cmts: el panel de serigrafia queda solo
    # con los labels de funcion, sin choques refdes-vs-label.
    sin_net = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        fp.Reference().SetLayer(
            pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab)
        fp.Value().SetLayer(pcbnew.Cmts_User)
        for pad in fp.Pads():
            num = pad.GetNumber()
            if not num:
                continue
            key = (ref, num)
            if key in netmap:
                pad.SetNet(nets[netmap[key]])
            else:
                sin_net.append(f"{ref}.{num}")

    # Pads mecanicos sin numero con anillo 0 -> NPTH (taladros del modulo LCD).
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNumber() == "" and pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
                pad.SetLocalClearance(mm(0.4))

    return len(faltan), sin_net, sin_lugar


def agregar_keepout(board):
    """Franja perimetral sin pistas ni vias.

    freerouting ignora el copper_edge_clearance de KiCad, asi que la
    restriccion tiene que existir como rule area o las pistas salen al borde.
    """
    e = EDGE_KEEPOUT
    k = pcbnew.ZONE(board)
    k.SetIsRuleArea(True)
    k.SetDoNotAllowTracks(True)
    k.SetDoNotAllowVias(True)
    k.SetDoNotAllowCopperPour(False)
    k.SetLayerSet(pcbnew.LSET.AllCuMask(4))
    o = k.Outline()
    o.NewOutline()
    for x, y in [(0, 0), (W, 0), (W, H), (0, H)]:
        o.Append(mm(x), mm(y))
    o.NewHole()
    for x, y in rounded_rect_pts(e, e, W - e, H - e, R=CORNER_R - e):
        o.Append(mm(x), mm(y), 0, 0)
    board.Add(k)


def _zona(board, layer, net, x0, y0, x1, y1, redondeada=True):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    if net is not None:
        z.SetNet(net)
    # 0.2 y no 0.25: con 0.25 el relleno no pasaba entre taladros vecinos y el
    # plano quedaba en 15 islas. El paso critico es la columna de pads del
    # socket U1 (2.54mm entre centros, pad de 1.7): con 0.25 de clearance el
    # cuello queda en 0.34mm y con min_thickness 0.25 apenas entra; a 0.2 el
    # cuello sube a 0.44 y pasa con margen.
    z.SetLocalClearance(mm(0.2))
    z.SetMinThickness(mm(0.2))
    # THT_THERMAL: conexion SOLIDA a pads SMD y vias, alivio termico solo en
    # los pasantes. Los pasantes son los que el usuario suelda a mano y con
    # conexion solida el plano les chupa el calor; los SMD los pone la maquina
    # y ahi el alivio termico solo agrega resistencia y estrangula la conexion
    # (2 starved_thermal en la corrida anterior).
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
    # Islas: se declara que se eliminen. ZONE_FILLER via scripting las ignora
    # (lección de V1), pero kicad-cli re-rellena internamente al correr el DRC
    # y ahi si lo respeta — que es el relleno que cuenta para la verificacion.
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = z.Outline()
    o.NewOutline()
    if redondeada:
        pts = rounded_rect_pts(x0, y0, x1, y1, R=CORNER_R - ZONE_MARGIN)
    else:
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for x, y in pts:
        o.Append(mm(x), mm(y))
    board.Add(z)
    return z


def agregar_zonas(board, nets):
    """Dos planos macizos: GND en In1.Cu y 3V3 en In2.Cu. Nada mas.

    In1.Cu entera para GND es todo el punto de las 4 capas: da plano de
    retorno continuo bajo el DAC y el op-amp, que en 2 capas era imposible
    con esta cantidad de THT.

    Lo que NO se hace, y por que:

    - NO hay vertido de GND en F.Cu ni en B.Cu. Con un plano interno macizo no
      aportan nada: las pistas los parten en islas, cada isla cuenta como GND
      sin conectar, y el DRC se llena de ruido que tapa los problemas reales.
      En la primera corrida de ruteo, 20 de 27 sin-conectar eran exactamente
      eso. Cada pad de GND llega al plano por via, que es lo que corresponde.

    - In2.Cu NO se parte en bandas por riel. Una banda cortada por las vias
      queda en islas y vuelve el mismo problema. In2.Cu es 3V3 entero —el riel
      mas repartido: display, DAC, expansores, microSD y MIDI— y VSYS y 5V van
      como PISTAS de la netclass Power (0.4mm). Alcanza de sobra: 5V alimenta
      solo al op-amp (~10mA) y VSYS al class-D, cuyos picos de cientos de mA
      entran comodos en 0.4mm.
    """
    m = ZONE_MARGIN
    _zona(board, pcbnew.In1_Cu, nets["GND"], m, m, W - m, H - m)
    _zona(board, pcbnew.In2_Cu, nets["3V3"], m, m, W - m, H - m)


def main():
    board = pcbnew.NewBoard(OUT)
    setup_stackup(board)

    netmap, nombres = load_netmap()
    nets = {}
    for name in sorted(nombres):
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n

    setup_netclasses(board)
    dibujar_contorno(board)
    n_grid, sin_net, sin_lugar = colocar(board, netmap, nets)
    agregar_keepout(board)
    agregar_zonas(board, nets)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(OUT, board)

    print(f"OK -> {OUT}")
    print(f"capas: {board.GetCopperLayerCount()}  "
          f"footprints: {len(list(board.GetFootprints()))}  "
          f"nets: {board.GetNetCount()}  zonas: {len(list(board.Zones()))}")
    print(f"empaquetados en el dorso: {n_grid - len(sin_lugar)} de {n_grid} pasivos")
    if sin_lugar:
        print(f"AVISO: {len(sin_lugar)} sin lugar en FREE_REGIONS "
              f"(quedaron en el origen): {', '.join(sin_lugar)}")
    if sin_net:
        print(f"AVISO: {len(sin_net)} pad(s) sin net: {', '.join(sin_net[:10])}")


if __name__ == "__main__":
    main()
