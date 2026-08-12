#!/usr/bin/env python3
"""Lectura y escritura de los DXF de layout. Python puro, SIN pcbnew.

Esta separacion es deliberada: el formato DXF es lo unico que hay entre el
proyecto KiCad y el Rhino del usuario, asi que conviene poder testearlo sin
levantar KiCad. gen_template_dxf.py y parse_dxf.py son cascaras finas que
extraen datos del board y delegan aca.

Convencion de ejes: KiCad tiene Y hacia ABAJO y DXF hacia ARRIBA. Todas las
coordenadas Y se niegan al escribir y se vuelven a negar al leer. Si esto se
rompe, el layout aparece espejado verticalmente en Rhino y es facil no
notarlo hasta que la placa esta fabricada.
"""
from collections import namedtuple

# ref  : refdes del componente (= nombre de la capa DXF)
# x, y : origen del footprint en mm, coordenadas KiCad
# bbox : (x0, y0, x1, y1) extension de los pads, coordenadas KiCad
# back : True si el componente esta en el dorso
Item = namedtuple("Item", "ref x y bbox back")

COLORS = [1, 2, 3, 4, 5, 6]   # rojo, amarillo, verde, cyan, azul, magenta
CROSS_ARM = 3.0               # mm de brazo de la cruz de origen


def _f(v):
    return f"{v:.4f}"


def line(layer, x1, y1, x2, y2, ltype="CONTINUOUS"):
    """Un LINE en la capa dada. Y se niega (ver nota de ejes del modulo)."""
    return (f"  0\nLINE\n  8\n{layer}\n  6\n{ltype}\n"
            f" 10\n{_f(x1)}\n 20\n{_f(-y1)}\n 30\n0.0\n"
            f" 11\n{_f(x2)}\n 21\n{_f(-y2)}\n 31\n0.0\n")


def text(layer, x, y, txt, h=1.8):
    return (f"  0\nTEXT\n  8\n{layer}\n"
            f" 10\n{_f(x)}\n 20\n{_f(-y)}\n 30\n0.0\n 40\n{_f(h)}\n  1\n{txt}\n")


def cross(layer, cx, cy, arm=CROSS_ARM):
    """Cruz de origen: las DOS lineas que parse_dxf busca para recuperar el
    centro. El formato de dos lineas cruzadas es lo que hace el round-trip
    robusto: el centro se recupera de la interseccion, asi que sobrevive a
    que Rhino reordene entidades o cambie el orden de los vertices."""
    return (line(layer, cx - arm, cy, cx + arm, cy) +
            line(layer, cx, cy - arm, cx, cy + arm))


def rect(layer, x0, y0, x1, y1, ltype="DASHED"):
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    out = ""
    for i in range(4):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % 4]
        out += line(layer, ax, ay, bx, by, ltype)
    return out


def build_document(outline, items):
    """DXF completo. `outline` es (x0, y0, x1, y1) del contorno de la placa."""
    x0, y0, x1, y1 = outline
    layers = [("BOARD_OUTLINE", 7)]
    for i, it in enumerate(items):
        layers.append((it.ref, COLORS[i % len(COLORS)]))

    out = []
    # $INSUNITS = 4 -> milimetros. Sin esto Rhino puede abrir el DXF en
    # pulgadas y el layout entero entra 25.4 veces mas chico.
    out.append("  0\nSECTION\n  2\nHEADER\n  9\n$INSUNITS\n 70\n4\n  0\nENDSEC\n")
    out.append("  0\nSECTION\n  2\nTABLES\n")
    out.append("  0\nTABLE\n  2\nLTYPE\n 70\n2\n")
    out.append("  0\nLTYPE\n  2\nCONTINUOUS\n 70\n0\n 72\n65\n 73\n0\n 40\n0.0\n")
    out.append("  0\nLTYPE\n  2\nDASHED\n 70\n0\n 72\n65\n 73\n2\n 40\n12.0\n"
               " 49\n6.0\n 74\n0\n 49\n-6.0\n 74\n0\n")
    out.append("  0\nENDTAB\n")
    out.append("  0\nTABLE\n  2\nLAYER\n")
    for name, color in layers:
        out.append(f"  0\nLAYER\n  2\n{name}\n 70\n0\n 62\n{color}\n  6\nCONTINUOUS\n")
    out.append("  0\nENDTAB\n  0\nENDSEC\n")

    out.append("  0\nSECTION\n  2\nENTITIES\n")
    for ax, ay, bx, by in [(x0, y0, x1, y0), (x1, y0, x1, y1),
                           (x1, y1, x0, y1), (x0, y1, x0, y0)]:
        out.append(line("BOARD_OUTLINE", ax, ay, bx, by))
    out.append(text("BOARD_OUTLINE", x0 + 1, y0 + 3,
                    f"PLACA {x1 - x0:.1f}x{y1 - y0:.1f}mm", h=2.5))

    for it in items:
        bx0, by0, bx1, by1 = it.bbox
        out.append(rect(it.ref, bx0, by0, bx1, by1))
        out.append(cross(it.ref, it.x, it.y))
        tag = f"{it.ref} (DORSO)" if it.back else it.ref
        out.append(text(it.ref, bx0, by1 + 2.0, tag))

    out.append("  0\nENDSEC\n  0\nEOF\n")
    return "".join(out)


# ------------------------------------------------------------------ lectura

def _groups(txt):
    """DXF es una lista plana de pares (codigo, valor) en lineas alternadas."""
    raw = [l.rstrip() for l in txt.splitlines()]
    out = []
    i = 0
    while i < len(raw) - 1:
        try:
            code = int(raw[i].strip())
        except ValueError:
            i += 1
            continue
        out.append((code, raw[i + 1].strip()))
        i += 2
    return out


def _lines_by_layer(txt):
    """{capa: [(x1, y1, x2, y2), ...]} en coordenadas KiCad (Y ya re-negada)."""
    groups = _groups(txt)
    by_layer = {}
    j = 0
    while j < len(groups):
        if groups[j] != (0, "LINE"):
            j += 1
            continue
        ent = {}
        j += 1
        while j < len(groups) and groups[j][0] != 0:
            ent[groups[j][0]] = groups[j][1]
            j += 1
        layer = ent.get(8, "")
        try:
            x1, y1 = float(ent.get(10, 0)), -float(ent.get(20, 0))
            x2, y2 = float(ent.get(11, 0)), -float(ent.get(21, 0))
        except ValueError:
            continue
        by_layer.setdefault(layer, []).append((x1, y1, x2, y2))
    return by_layer


def _cross_center(segs, tol=1e-3):
    """Centro de la cruz formada por una horizontal y una vertical que se
    cruzan EN SU PUNTO MEDIO. Devuelve None si la capa no tiene ese par.

    Se busca por geometria y no por orden de aparicion, porque Rhino puede
    reordenar o reescribir las entidades al guardar.

    La condicion de punto medio no es un detalle: el rectangulo punteado del
    bbox vive en la MISMA capa y tambien tiene horizontales y verticales que
    se tocan. Lo que descarta sus esquinas es exigir que el cruce caiga en la
    mitad de ambos segmentos.
    """
    horiz = [s for s in segs if abs(s[3] - s[1]) < tol and abs(s[2] - s[0]) > tol]
    vert = [s for s in segs if abs(s[2] - s[0]) < tol and abs(s[3] - s[1]) > tol]
    for h in horiz:
        hy = h[1]
        hx0, hx1 = sorted((h[0], h[2]))
        for v in vert:
            vx = v[0]
            vy0, vy1 = sorted((v[1], v[3]))
            if not (hx0 - tol <= vx <= hx1 + tol and vy0 - tol <= hy <= vy1 + tol):
                continue
            if abs((hx0 + hx1) / 2 - vx) < tol and abs((vy0 + vy1) / 2 - hy) < tol:
                return (vx, hy)
    return None


def read_positions(txt):
    """{refdes: (x, y)} leido de las cruces de origen del DXF."""
    out = {}
    for layer, segs in _lines_by_layer(txt).items():
        if layer == "BOARD_OUTLINE":
            continue
        c = _cross_center(segs)
        if c is not None:
            out[layer] = c
    return out


def read_outline(txt):
    """(x0, y0, x1, y1) del contorno, para que el usuario pueda cambiar el
    tamano de la placa en Rhino y no solo mover componentes."""
    segs = _lines_by_layer(txt).get("BOARD_OUTLINE", [])
    if not segs:
        raise ValueError("el DXF no tiene capa BOARD_OUTLINE")
    xs = [v for s in segs for v in (s[0], s[2])]
    ys = [v for s in segs for v in (s[1], s[3])]
    return (min(xs), min(ys), max(xs), max(ys))
