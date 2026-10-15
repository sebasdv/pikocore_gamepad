#!/usr/bin/env python3
"""Vias de conexion a plano para los pads SMD de GND y 3V3.

Correr con el python de KiCad, DESPUES de gen_pcb.py y ANTES de
route_io.py export.

EL ORDEN IMPORTA Y NO ES EL INTUITIVO. La primera version de este script
corria despues del ruteo, que parecia lo natural: primero las senales, despues
"rellenar" las conexiones a plano que faltaban. Sale mal. Con el ruteo ya
hecho, poner una via en el centro de cada pad la mete encima de pistas de
otras nets que ya pasan por ahi: 12 cortocircuitos y 22 violaciones de margen
en la corrida donde se probo.

Puestas ANTES, las vias entran al DSN como parte del board y freerouting las
esquiva igual que a cualquier otro obstaculo.

POR QUE HACE FALTA UN SCRIPT Y NO LO HACE FREEROUTING:

Los planos viven en las capas internas (GND en In1, 3V3 en In2) y route_io.py
las exporta al DSN como (type power) para que freerouting NO rutee senales
encima y las parta. El efecto colateral es que freerouting deja de verlas como
destino: no pone ni una via hacia ellas. Los pads THT no lo necesitan —el
taladro ya atraviesa todas las capas— pero los 42 pads SMD de GND/3V3 quedan
"unconnected" aunque el plano este relleno justo debajo.

Se probo antes meter GND en la netclass Power (que en el DSN es lo que declara
la via a usar). No alcanza: freerouting sigue sin bajar a una capa (type
power), sin importar la clase. Por eso las vias se colocan aca, que ademas es
determinista y no depende de lo que el autorouter decida en cada corrida.

POR QUE ESTO NO CONTRADICE EL "NO STITCHING" DE finish_pcb.py:

Ahi se descarto agregar vias de stitching, que son vias de GND puestas en
lugares arbitrarios para coser islas del plano. Aquellas no conectaban nada
—tocaban el plano interno y nada mas— y el DRC las reportaba como
via_dangling. Estas son otra cosa: cada una nace EN un pad y termina en el
plano de SU MISMA net, o sea que es la conexion que al pad le falta. Sin ella
el pad no tiene forma de llegar al plano.

VIAS PASANTES Y NO CIEGAS: una via F.Cu->B.Cu atraviesa los dos planos, pero
solo se conecta al que comparte su net; para el otro el relleno de zona abre
un despeje alrededor. Es lo mismo que ya hacen las 38 vias que pone
freerouting para las senales. Las vias ciegas/enterradas encarecerian la
placa sin ganar nada.

CUANDO NO ENTRA LA VIA EN EL CENTRO DEL PAD:

Pads adyacentes de nets distintas y paso fino no dejan lugar para dos vias, ni
siquiera chicas: a 0.65mm de paso harian falta d1 + d2 <= 0.9mm y la via chica
ya es 0.5 cada una. En ese caso el script desplaza la via a un punto libre
cercano y la une al pad con un tramo corto de pista — el fanout de toda la
vida — en vez de rendirse.

Rendirse tambien "funciona": el pad queda sin via y freerouting suele llevarlo
al plano por pista. El problema es que suele. Freerouting da un ruteo distinto
en cada corrida (503 pistas una vez, 477 la siguiente sobre la misma placa), y
un pad que llega al plano porque al autorouter le salio es una placa que anda
de casualidad. Con U5.20 directamente no le salio, dos veces seguidas.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "pikocore_gamepad.kicad_pcb")

# net -> capa donde vive su plano. Si se agrega un plano nuevo, va aca.
PLANOS = {"GND": "GND", "3V3": "PWR"}

# Misma via que declara la netclass Power en el DSN (600um / 300um), asi que
# la placa no estrena una geometria de taladro solo por estas vias.
VIA_D = 0.6
VIA_DRILL = 0.3

# Via chica para pads apretados: 0.50/0.25, anillo 0.125. Era 0.50/0.30
# (anillo 0.100): con el margen de 0.127 de las senales del chip-down una pista
# vecina quedaba a 0.23mm del taladro, bajo el hole_clearance de 0.25. El
# taladro de 0.25 ya existe en la placa (vias del nucleo RP2350A).
VIA_D_MIN = 0.5
VIA_DRILL_MIN = 0.25

# Margen a respetar contra el cobre vecino (el clearance general del proyecto).
CLEARANCE = 0.2

# Hueco libre que necesita cada tamano de via alrededor del centro del pad.
HUECO_NORMAL = VIA_D / 2 + CLEARANCE      # 0.50mm
HUECO_MIN = VIA_D_MIN / 2 + CLEARANCE     # 0.45mm

# --- fanout: via desplazada + tramo, para el pad donde no entra la via ---

# Ancho del tramo pad->via. Es el track_width de la netclass Power, que es la
# que llevan GND y 3V3: el tramo no tiene por que ser mas fino que la pista
# que freerouting habria trazado hasta ahi. Es un TECHO, no un valor fijo —
# ver ancho_stub().
ANCHO_STUB = 0.4

# Piso del ancho del tramo: el track_width de la netclass Default. Mas fino
# que esto no se traza; si no entra, no hay fanout y el pad va a sin_lugar.
ANCHO_STUB_MIN = 0.2

# Distancias a probar, de menor a mayor. Cuanto mas corto el tramo, menos
# cobre nuevo se mete en una zona que ya estaba apretada, asi que gana la
# primera que entre. Mas de 1.3mm ya no es un fanout: es ruteo, y eso es
# trabajo de freerouting.
DIST_FANOUT = (0.7, 0.9, 1.1, 1.3)
PASO_ANG = 15

# Puntos intermedios que se muestrean sobre el tramo. Que los dos extremos
# esten libres no dice nada del camino entre ellos.
MUESTRAS_STUB = 6


def mm(v):
    return pcbnew.FromMM(v)


def pads_sin_plano(board):
    """Pads SMD cuya net tiene plano y que por lo tanto necesitan via."""
    out = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNumber():
                continue
            if pad.GetNetname() not in PLANOS:
                continue
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                continue          # el taladro ya cruza todas las capas
            # Pad expuesto con vias termicas en el footprint (U7 TPS63001,
            # U1 RP2350A): son PTH con el mismo numero y ya bajan al plano.
            # Una via mas ahi quedaba a 0.125mm de una termica (hole_to_hole).
            if any(q.GetNumber() == pad.GetNumber()
                   and q.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
                   for q in fp.Pads()):
                continue
            out.append((fp.GetReference(), pad))
    return out


def ya_tiene_via(board, pad, tol=0.05):
    """True si ya hay una via de la misma net encima del pad.

    Evita duplicar cuando el script se corre dos veces sobre el mismo board, o
    cuando freerouting si llego a poner la via.
    """
    px, py = pad.GetPosition().x, pad.GetPosition().y
    for t in board.GetTracks():
        if t.GetClass() != "PCB_VIA":
            continue
        if t.GetNetname() != pad.GetNetname():
            continue
        d = ((t.GetPosition().x - px) ** 2 + (t.GetPosition().y - py) ** 2) ** 0.5
        if d <= mm(tol):
            return True
    return False


# Distancia minima entre centros de dos vias de la MISMA net. Taladro 0.3 +
# el hole_to_hole minimo de la placa (0.25) = 0.55; 0.6 deja margen.
VIA_VECINA = 0.6


def via_misma_net_cerca(board, x, y, net, d=VIA_VECINA):
    """True si ya hay una via de `net` a menos de `d` mm de (x, y)."""
    for t in board.GetTracks():
        if t.GetClass() != "PCB_VIA" or t.GetNetname() != net:
            continue
        v = t.GetPosition()
        if math.hypot(pcbnew.ToMM(v.x) - x, pcbnew.ToMM(v.y) - y) < d:
            return True
    return False


def via_vecina_misma_net(board, pad, d=VIA_VECINA):
    """True si ya hay una via de la net del pad a menos de `d` mm."""
    c = pad.GetPosition()
    return via_misma_net_cerca(board, pcbnew.ToMM(c.x), pcbnew.ToMM(c.y),
                               pad.GetNetname(), d)


def hueco_libre(board, pad):
    """Distancia del CENTRO del pad al cobre ajeno mas cercano, en mm.

    Mira dos cosas, las dos de OTRA net: los pads, que es lo que limita el
    diametro de la via en el caso general, y las VIAS YA PUESTAS — incluidas
    las que coloco este mismo script mas temprano en esta corrida. Las pistas
    no se consideran porque este script corre ANTES del ruteo.

    Lo de las vias faltaba y era un bug. Cada via se dimensionaba mirando solo
    pads, asi que dos pads adyacentes de nets distintas recibian cada uno su
    via de 0.5mm sin enterarse el uno del otro, y las dos terminaban a 0.150mm
    entre bordes contra los 0.2mm que pide la netclass. Paso con U5, un
    TSSOP-20 de paso 0.65mm (pads 8/9 y 19/20, GND contra 3V3): dos
    infracciones que el DRC recien reporta despues del ruteo, cuando
    rehacerlo cuesta un ciclo entero.

    A 0.65mm de paso no hay diametro que salve a las dos EN EL CENTRO de sus
    pads: harian falta d1 + d2 <= 0.9mm y la via chica ya es 0.5 cada una.
    Bajarla a 0.4 con el taladro de 0.3 romperia el anillo minimo de 0.100mm
    del proyecto. La segunda va entonces por fanout (ver lugar_para_via), que
    la desplaza a un punto libre cercano. Cual de las dos se queda en el centro
    depende del orden de iteracion: es deterministico, y siendo GND y 3V3 las
    dos con plano, da igual cual sea.
    """
    return hueco_en(board, pcbnew.ToMM(pad.GetPosition().x),
                    pcbnew.ToMM(pad.GetPosition().y), pad.GetNetname())


def hueco_en(board, x, y, net):
    """Igual que hueco_libre pero para un punto cualquiera, no para un pad.

    Hace falta suelto porque el fanout tiene que medir el hueco en lugares
    donde no hay ningun pad: el destino de la via desplazada y los puntos
    intermedios del tramo.
    """
    best = float("inf")

    # Vias de otra net: el borde de cobre esta a `radio` del centro de la via,
    # asi que lo que limita es la distancia entre centros menos ese radio.
    for t in board.GetTracks():
        if t.GetClass() != "PCB_VIA":
            continue
        if t.GetNetname() == net:
            continue
        vx = pcbnew.ToMM(t.GetPosition().x)
        vy = pcbnew.ToMM(t.GetPosition().y)
        d = math.hypot(vx - x, vy - y)
        # GetWidth() sin argumento existe pero dispara un assert en KiCad 9:
        # una via puede tener diametro distinto por capa. Estas son pasantes y
        # uniformes, asi que F_Cu describe la via entera.
        best = min(best, d - pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2.0)

    for fp in board.GetFootprints():
        for q in fp.Pads():
            if not q.GetNumber():
                continue
            if q.GetNetname() == net:
                # Cobre de la misma net no estorba, pero su TALADRO si: las
                # vias termicas de U7 dejaron una via de PGND a 0.125mm de
                # una de ellas (hole_to_hole, minimo 0.25). Taladro mas
                # grande que pone este script: 0.3.
                if q.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                    qx = pcbnew.ToMM(q.GetPosition().x)
                    qy = pcbnew.ToMM(q.GetPosition().y)
                    lim = pcbnew.ToMM(q.GetDrillSizeX()) / 2 + 0.15 + 0.25
                    if math.hypot(qx - x, qy - y) < lim:
                        return 0.0
                continue
            bb = q.GetBoundingBox()
            dx = max(0.0, max(pcbnew.ToMM(bb.GetLeft()) - x,
                              x - pcbnew.ToMM(bb.GetRight())))
            dy = max(0.0, max(pcbnew.ToMM(bb.GetTop()) - y,
                              y - pcbnew.ToMM(bb.GetBottom())))
            best = min(best, math.hypot(dx, dy))

    # PISTAS y ZONAS de otra net, y keepouts. Desde el chip-down la placa ya
    # tiene cobre antes del ruteo: el nucleo del RP2350A copiado de la placa
    # oficial (pistas y zonas de 1V1, VREG_LX, GND) y las pistas manuales.
    # Sin esto el script metia vias de 3V3 dentro de la zona de VREG_LX del
    # regulador —que el relleno despues esquiva, deformando justo el cobre
    # que la guia de Raspberry Pi pide no tocar— y en el anillo de keepout
    # de los NPTH del USB-C.
    for t in board.GetTracks():
        if t.GetClass() != "PCB_TRACK" or t.GetNetname() == net:
            continue
        a, b = t.GetStart(), t.GetEnd()
        d = _dist_segmento(x, y, pcbnew.ToMM(a.x), pcbnew.ToMM(a.y),
                           pcbnew.ToMM(b.x), pcbnew.ToMM(b.y))
        best = min(best, d - pcbnew.ToMM(t.GetWidth()) / 2.0)
    for z in board.Zones():
        ol = z.Outline()
        if z.GetIsRuleArea():
            # Un keepout cuenta como cobre ajeno: la via no puede ni pisarlo
            # con su radio (medir solo el centro dejaba vias de GND del USB-C
            # rozando el anillo de sus NPTH).
            if z.GetDoNotAllowVias():
                best = min(best, _dist_poligono(ol, x, y))
            continue
        if z.GetNetname() == net:
            continue
        if not (z.IsOnLayer(pcbnew.F_Cu) or z.IsOnLayer(pcbnew.B_Cu)):
            continue          # los planos internos se apartan solos
        best = min(best, _dist_poligono(ol, x, y))
    return best


def _dist_segmento(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _dist_poligono(outline, x, y):
    """Distancia del punto al contorno de la zona; 0 si esta adentro."""
    if outline.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))):
        return 0.0
    best = float("inf")
    ol = outline.Outline(0)
    n = ol.PointCount()
    for i in range(n):
        a, b = ol.CPoint(i), ol.CPoint((i + 1) % n)
        best = min(best, _dist_segmento(x, y, pcbnew.ToMM(a.x), pcbnew.ToMM(a.y),
                                        pcbnew.ToMM(b.x), pcbnew.ToMM(b.y)))
    return best


def ancho_stub(h):
    """Ancho del tramo que sale de un pad con `h` mm de hueco, o None.

    Esto es lo que hace falta y no es obvio: la pista ARRANCA en el centro del
    pad, y ahi su punta redondeada se expande media anchura en TODAS las
    direcciones, tambien hacia el vecino que dejo sin lugar a la via. O sea que
    el tramo tiene que caber en el mismo hueco que rechazo la via, aunque se
    vaya para el otro lado.

    Se descubrio por un DRC: el tramo de U2.4 salia en direccion contraria al
    pad 5 y lo violaba igual, con 0.125mm reales — que es exactamente el hueco
    del pad (0.325) menos el radio de la punta (0.200). La cuenta cierra al
    micron, y no hay direccion de salida que lo salve.

    Por eso el ancho no es fijo: se achica hasta lo que el hueco permita, con
    ANCHO_STUB de techo y ANCHO_STUB_MIN de piso.
    """
    ancho = min(ANCHO_STUB, 2.0 * (h - CLEARANCE))
    return ancho if ancho >= ANCHO_STUB_MIN else None


def lugar_para_via(board, pad, diam, ancho):
    """Punto (x, y) en mm donde SI entra una via de `diam` unida al pad, o None.

    Barre en circulo alrededor del pad, de mas cerca a mas lejos. La distancia
    manda —el tramo mas corto es el que menos cobre nuevo mete en una zona que
    ya estaba apretada— y dentro de cada distancia gana la direccion con mas
    holgura, no la primera que entra.

    Chequea el tramo entero, no solo el destino. Un extremo libre con el camino
    tapado seria un corto, que es peor que el problema que se venia a resolver.
    """
    px = pcbnew.ToMM(pad.GetPosition().x)
    py = pcbnew.ToMM(pad.GetPosition().y)
    net = pad.GetNetname()
    necesita_via = diam / 2.0 + CLEARANCE
    necesita_pista = ancho / 2.0 + CLEARANCE

    for dist in DIST_FANOUT:
        candidatos = []
        for paso in range(360 // PASO_ANG):
            ang = math.radians(paso * PASO_ANG)
            x = px + dist * math.cos(ang)
            y = py + dist * math.sin(ang)
            h_via = hueco_en(board, x, y, net)
            if h_via < necesita_via:
                continue
            # hueco_en ignora el cobre de la MISMA net, asi que dos fanouts
            # vecinos del conector del FPC (3V3 en los pads 4/5/6, GND en
            # 13..20) elegian el mismo punto y quedaban con los taladros a
            # 0.01mm: hole_to_hole en el DRC. Una via propia tambien ocupa.
            if via_misma_net_cerca(board, x, y, net):
                continue
            if all(hueco_en(board, px + (x - px) * k / MUESTRAS_STUB,
                            py + (y - py) * k / MUESTRAS_STUB,
                            net) >= necesita_pista
                   for k in range(1, MUESTRAS_STUB)):
                candidatos.append((h_via, x, y))
        if candidatos:
            # De las direcciones que entran, gana la MAS HOLGADA, no la
            # primera. Cumplir el margen no alcanza: esta via tambien es un
            # obstaculo para el ruteo que viene despues, y dejarla apretada
            # contra el camino de escape de un pad vecino le come el lugar a
            # freerouting. Paso con U2: la via cumplia contra el pad 5 por
            # 0.037mm de sobra, y despues freerouting saco BOOST_SW de ese
            # mismo pad y le paso a 0.150mm. Poner la via donde hay lugar de
            # sobra sale gratis y evita esa clase de choque.
            return max(candidatos)[1:]
    return None


def poner_stub(board, pad, x, y, diam, ancho):
    """Via desplazada en (x, y) mas el tramo que la une al pad.

    El tramo va en la capa del pad: el pad es SMD, asi que vive en una sola
    capa y ahi es donde hay que salir.

    OJO CON pad.GetLayer(): en un footprint volteado devuelve F.Cu aunque el
    unico cobre del pad este en B.Cu. Con el se colocaban los tres tramos en la
    cara equivocada: no conectaban nada, quedaban de cobre huerfano y el DRC
    los reportaba como track_dangling. GetLayerSet().CuStack() si dice la
    verdad, y para un pad SMD trae exactamente una capa.
    """
    capa = pad.GetLayerSet().CuStack()[0]

    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    # Con capa: en KiCad 9.0.1 SetWidth(int) dispara un assert modal y el
    # script queda colgado esperando un click (ver manual_tracks.py).
    v.SetWidth(pcbnew.PADSTACK.ALL_LAYERS, mm(diam))
    v.SetDrill(mm(VIA_DRILL if diam >= VIA_D else VIA_DRILL_MIN))
    v.SetNet(pad.GetNet())
    board.Add(v)

    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pad.GetPosition())
    t.SetEnd(pcbnew.VECTOR2I(mm(x), mm(y)))
    t.SetWidth(mm(ancho))
    t.SetLayer(capa)
    t.SetNet(pad.GetNet())
    board.Add(t)
    return v


def poner_via(board, pad, diam):
    """Via pasante en el centro del pad, en la net del pad."""
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pad.GetPosition())
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    # Con capa: en KiCad 9.0.1 SetWidth(int) dispara un assert modal y el
    # script queda colgado esperando un click (ver manual_tracks.py).
    v.SetWidth(pcbnew.PADSTACK.ALL_LAYERS, mm(diam))
    v.SetDrill(mm(VIA_DRILL if diam >= VIA_D else VIA_DRILL_MIN))
    v.SetNet(pad.GetNet())
    board.Add(v)
    return v


def main():
    if not os.path.isfile(PCB):
        print(f"FALTA: {PCB}")
        return 1
    board = pcbnew.LoadBoard(PCB)

    pend = pads_sin_plano(board)
    puestas = chicas = saltadas = desplazadas = 0
    fanouts = []
    sin_lugar = []
    vecinas = 0
    for ref, pad in pend:
        if ya_tiene_via(board, pad):
            saltadas += 1
            continue
        if via_vecina_misma_net(board, pad):
            # Pads de la misma net a paso fino (los 13 GND del conector del
            # FPC, a 0.5mm): una via por pad deja los taladros a 0.2mm y el
            # DRC reporta hole_to_hole. Con una via cada dos pads los
            # taladros quedan a 0.7mm, y el pad sin via lo une freerouting
            # al vecino con una pista de medio milimetro.
            vecinas += 1
            continue
        h = hueco_libre(board, pad)
        if h >= HUECO_NORMAL:
            poner_via(board, pad, VIA_D)
            puestas += 1
        elif h >= HUECO_MIN:
            poner_via(board, pad, VIA_D_MIN)
            chicas += 1
        else:
            # No entra ni la chica en el centro del pad. Antes de rendirse,
            # desplazarla: la via se corre a un punto libre cercano y un tramo
            # corto la une al pad. Nunca se fuerza una via encima — eso seria
            # un corto, que es peor que el problema.
            ancho = ancho_stub(h)
            destino = lugar_para_via(board, pad, VIA_D_MIN, ancho) if ancho else None
            if destino:
                poner_stub(board, pad, destino[0], destino[1], VIA_D_MIN, ancho)
                desplazadas += 1
                dx = destino[0] - pcbnew.ToMM(pad.GetPosition().x)
                dy = destino[1] - pcbnew.ToMM(pad.GetPosition().y)
                fanouts.append(f"{ref}.{pad.GetNumber()} "
                               f"[{pad.GetNetname()}] hueco={h:.3f}mm -> via a "
                               f"{math.hypot(dx, dy):.2f}mm, tramo {ancho:.2f}mm")
            else:
                sin_lugar.append(f"{ref}.{pad.GetNumber()} "
                                 f"[{pad.GetNetname()}] hueco={h:.3f}mm")

    pcbnew.SaveBoard(PCB, board)
    vias = len([t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"])
    print(f"pads SMD sobre plano: {len(pend)}")
    print(f"vias {VIA_D}mm: {puestas}   vias {VIA_D_MIN}mm: {chicas}   "
          f"ya tenian: {saltadas}   desplazadas: {desplazadas}   "
          f"saltadas por via vecina: {vecinas}")
    if fanouts:
        print(f"VIA DESPLAZADA + tramo ({len(fanouts)}) — no entraba en el "
              f"centro del pad:")
        for f in fanouts:
            print(f"  {f}")
    if sin_lugar:
        print(f"SIN VIA por falta de espacio ({len(sin_lugar)}) — tienen que "
              f"llegar al plano por pista:")
        for s in sin_lugar:
            print(f"  {s}")
    print(f"guardado: {PCB}  ({vias} vias en total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
