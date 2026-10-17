#!/usr/bin/env python3
"""Genera los footprints propios en lib/gamesetup_fp.pretty.

Python puro, sin pcbnew: escribe los .kicad_mod como texto. Eso permite
testear la geometria con unittest sin levantar KiCad, que es donde estan los
errores caros — un pad corrido no lo ve nadie hasta que la placa llega.

Toda cota fisica sale de params.py, nunca de un numero suelto aca.

Footprints:
  - LCD_ST7789_240x240_7P : el modulo IPS de 1.3 pulgadas, 7 pines pasantes.
                         Geometria: pads, contorno, area activa y agujeros
                         del modulo (estos solo como dibujo, no se taladran).
  - RP2350-Plus_Castellated : el modulo se suelda plano al dorso por sus
                         castellations; se deriva de la huella oficial de la
                         Pico (KiCad), sin agujeros de montaje ni pads D1-D3.

ORIGEN del footprint de la pantalla = PIN 1 (GND), X a lo largo de la fila
de pines, Y hacia el cuerpo: la posicion se verifica con una regla sobre la
placa impresa.
"""
import itertools
import os
import re
import uuid as uuidlib

import params

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "lib", "gamesetup_fp.pretty")

LCD_NAME = "LCD_ST7789_240x240_7P"
LCD_PIN_NAMES = ["GND", "VCC", "SCL", "SDA", "RES", "DC", "BLK"]

# UUIDs deterministicos: regenerar con las mismas cotas da el mismo archivo
# byte a byte (git no ve cambios falsos y el test compara el archivo entero).
_ids = itertools.count()


def u():
    return str(uuidlib.uuid5(uuidlib.NAMESPACE_URL, f"gen_fp/{next(_ids)}"))


def F(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


# ---------------------------------------------------------------- geometria
# Todo relativo al PIN 1. En coordenadas del modulo (esquina del lado de los
# pines = 0,0) el pin 1 esta en (LCD7_PIN1_X, LCD7_PIN_ROW_TO_EDGE).

def _origen():
    return params.v("LCD7_PIN1_X"), params.v("LCD7_PIN_ROW_TO_EDGE")


def lcd_pads():
    """Los 7 pines, con el pin 1 en (0, 0)."""
    pitch = params.v("LCD7_PIN_PITCH")
    return [{"num": i + 1, "name": n, "x": i * pitch, "y": 0.0,
             "drill": params.v("LCD7_PIN_DRILL"),
             "size": params.v("LCD7_PIN_PAD")}
            for i, n in enumerate(LCD_PIN_NAMES)]


def lcd_outline():
    """Contorno de la placa del modulo."""
    ox, oy = _origen()
    return {"x0": -ox, "y0": -oy,
            "x1": params.v("LCD7_BOARD_W") - ox,
            "y1": params.v("LCD7_BOARD_H") - oy}


def lcd_window():
    """Area activa. Es la ventana a recortar en la tapa del enclosure."""
    ox, oy = _origen()
    x0 = params.v("LCD7_AA_OFF_X") - ox
    y0 = params.v("LCD7_AA_OFF_TOP") - oy
    a = params.v("LCD7_AA")
    return {"x0": x0, "y0": y0, "x1": x0 + a, "y1": y0 + a}


def lcd_holes():
    """Los 4 agujeros de montaje del modulo. Solo dibujo: en la placa no se
    taladran, el modulo se sostiene por sus pines."""
    c = lcd_outline()
    i = params.v("LCD7_HOLE_INSET")
    return [{"x": x, "y": y, "drill": params.v("LCD7_HOLE_DIA")}
            for y in (c["y0"] + i, c["y1"] - i)
            for x in (c["x0"] + i, c["x1"] - i)]


# ---------------------------------------------------------------- escritura

def _line(layer, x0, y0, x1, y1, w=0.12):
    return (f'  (fp_line (start {F(x0)} {F(y0)}) (end {F(x1)} {F(y1)}) '
            f'(stroke (width {F(w)}) (type solid)) (layer "{layer}") '
            f'(uuid "{u()}"))\n')


def _box(layer, x0, y0, x1, y1, w=0.12):
    return (_line(layer, x0, y0, x1, y0, w) + _line(layer, x1, y0, x1, y1, w) +
            _line(layer, x1, y1, x0, y1, w) + _line(layer, x0, y1, x0, y0, w))


def _circle(layer, x, y, r, w=0.12):
    return (f'  (fp_circle (center {F(x)} {F(y)}) (end {F(x + r)} {F(y)}) '
            f'(stroke (width {F(w)}) (type solid)) (fill none) '
            f'(layer "{layer}") (uuid "{u()}"))\n')


def build_lcd():
    """El .kicad_mod del modulo, todo desde LCD7_* via lcd_*()."""
    global _ids
    _ids = itertools.count()
    c, win = lcd_outline(), lcd_window()
    pads = lcd_pads()
    ref_x = pads[3]["x"]      # refdes centrado: no pisa las etiquetas GND/BLK
    out = [
        f'(footprint "{LCD_NAME}"\n',
        '  (version 20240108)\n',
        '  (generator "gen_fp.py")\n',
        '  (layer "F.Cu")\n',
        '  (attr through_hole)\n',
        '  (descr "Modulo IPS 1.3in 240x240 ST7789, 7 pines pasantes, header '
        'soldado directo. Origen = pin 1 (GND). Cotas de params.py (LCD7_*). '
        'Los 4 agujeros del modulo van solo dibujados (Cmts.User/F.Fab), no se '
        'taladran. El rectangulo interior de Cmts.User es el area activa: es '
        'lo que hay que recortar en la tapa del enclosure.")\n',
        f'  (property "Reference" "J**" (at {F(ref_x)} -3 0) (layer "F.SilkS") '
        f'(uuid "{u()}") (effects (font (size 1 1) (thickness 0.15))))\n',
        f'  (property "Value" "{LCD_NAME}" (at 0 -5 0) (layer "F.Fab") '
        f'(uuid "{u()}") (effects (font (size 1 1) (thickness 0.15))))\n',
    ]
    for p in pads:
        out.append(f'  (pad "{p["num"]}" thru_hole '
                   f'{"rect" if p["num"] == 1 else "circle"} '
                   f'(at {F(p["x"])} {F(p["y"])}) (size {F(p["size"])} {F(p["size"])}) '
                   f'(drill {F(p["drill"])}) (layers "*.Cu" "*.Mask") '
                   f'(pinfunction "{p["name"]}") (uuid "{u()}"))\n')
    # Contorno del modulo: Fab (documentacion), CrtYd (lo que ocupa en el
    # frente) y Cmts (guia para Rhino), mas el area activa.
    out.append(_box("F.Fab", c["x0"], c["y0"], c["x1"], c["y1"]))
    out.append(_box("F.CrtYd", c["x0"], c["y0"], c["x1"], c["y1"], 0.05))
    out.append(_box("Cmts.User", c["x0"], c["y0"], c["x1"], c["y1"]))
    out.append(_box("Cmts.User", win["x0"], win["y0"], win["x1"], win["y1"], 0.2))
    for layer in ("Cmts.User", "F.Fab"):
        for h in lcd_holes():
            out.append(_circle(layer, h["x"], h["y"], h["drill"] / 2))
    # Orientacion al soldar: GND sobre el pad cuadrado, BLK en el otro
    # extremo. Entre el borde del modulo (y=-1.27) y el de la placa.
    for p in (pads[0], pads[-1]):
        out.append(f'  (fp_text user "{p["name"]}" (at {F(p["x"])} -2.2 0) '
                   f'(layer "F.SilkS") (uuid "{u()}") '
                   f'(effects (font (size 1 1) (thickness 0.15))))\n')
    out.append(')\n')
    return "".join(out)


# NOTA: el jack 3.5mm ya NO se genera aca. Se dibujo un footprint propio y
# estaba MAL: las cotas 1.20/3.60/7.30/9.10/12.80 del "Recommended PCB
# Layout" del datasheet son VERTICALES y se leyeron como horizontales, con
# lo que salia un patron ancho y bajo en vez de alto y angosto. Se detecto
# porque el modelo 3D del fabricante no calzaba sobre los pads.
# Ahora se usa el OFICIAL de KiCad 9:
#   Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal
# Sus pads se llaman por funcion (S/T/R/TN/RN), no por numero.
#
# El MODELO 3D si vive en este repo: KiCad 9.0.4 declara el .step en el
# footprint pero NO lo incluye en la instalacion (estan los del
# 3523N/3524N/3525N, no el del 3535NG). El .wrl de
# lib/gamesetup_fp.3dshapes/ se armo desde el modelo de Same Sky, alineado
# con el origen del footprint oficial (pad S). Se referencia desde
# placements/gen_pcb, no desde aca, porque el footprint no es nuestro.


# El modulo (Waveshare RP2350-Plus, 21x51mm) tiene la misma geometria de pads
# que la Pico, asi que se deriva de la huella oficial de KiCad. Su modelo 3D
# (RP2350-Plus_Module.step) lo asigna gen_pcb.py via MODELOS_PROPIOS.
KICAD_SHARE_FP = "C:/Program Files/KiCad/9.0/share/kicad/footprints"
PICO_SMD_HAND = os.path.join(KICAD_SHARE_FP, "Module.pretty",
                             "RaspberryPi_Pico_SMD_HandSolder.kicad_mod")
CASTELLATED_NAME = "RP2350-Plus_Castellated"


def _quitar_pads(s, quitar):
    """Quita de un .kicad_mod los bloques (pad ...) para los que quitar(bloque)
    es verdadero, contando parentesis (respeta los strings entre comillas).
    El resto del texto queda byte a byte igual."""
    out, i = [], 0
    while True:
        j = s.find("(pad ", i)
        if j < 0:
            out.append(s[i:])
            return "".join(out)
        depth, k, en_str = 0, j, False
        while True:
            c = s[k]
            if en_str:
                if c == "\\":
                    k += 1
                elif c == '"':
                    en_str = False
            elif c == '"':
                en_str = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        k += 1
        if quitar(s[j:k]):
            # tambien el salto de linea y la indentacion que precedian al pad
            ini = j
            while ini > i and s[ini - 1] in "\t ":
                ini -= 1
            if ini > i and s[ini - 1] == "\n":
                ini -= 1
                if ini > i and s[ini - 1] == "\r":
                    ini -= 1
            out.append(s[i:ini])
        else:
            out.append(s[i:k])
        i = k


def derivar_modulo_castellated():
    """Huella oficial de la Pico (SMD hand solder) sin los 4 agujeros de
    montaje (el modulo no los tiene y su dorso debe quedar libre) ni los pads
    de depuracion D1-D3, ni la pasta sin nombre que la huella trae para esos
    tres (bajo el modulo, un esten imprimiria bolitas de estano). Quedan los
    pads 1-40 y los 40 de pasta sin nombre de las pastillas."""
    if not os.path.isfile(PICO_SMD_HAND):
        print(f"AVISO: no se encontro {PICO_SMD_HAND}")
        return False
    with open(PICO_SMD_HAND, encoding="utf-8", newline="") as f:
        s = f.read()

    def quitar(bloque):
        if bloque.startswith('(pad ""'):
            # La pasta de D1-D3 esta en x -2.54/0/2.54; la de las pastillas en
            # x +-8.89.
            x = float(re.search(r"\(at\s+([-\d.]+)", bloque).group(1))
            return abs(x) < 8
        return ("np_thru_hole" in bloque[:30]
                or bloque.startswith(('(pad "D1"', '(pad "D2"', '(pad "D3"')))

    s = _quitar_pads(s, quitar)
    s = s.replace("${KICAD9_3DMODEL_DIR}/Module.3dshapes/RaspberryPi_Pico.wrl",
                  "${KIPRJMOD}/lib/gamesetup_fp.3dshapes/RP2350-Plus_Module.step")
    s = s.replace('(footprint "RaspberryPi_Pico_SMD_HandSolder"',
                  f'(footprint "{CASTELLATED_NAME}"')
    with open(os.path.join(OUT, CASTELLATED_NAME + ".kicad_mod"), "w",
              encoding="utf-8", newline="") as f:
        f.write(s)
    return True


def main():
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, LCD_NAME + ".kicad_mod")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(build_lcd())
    print(f"OK -> {path}")
    if derivar_modulo_castellated():
        print(f"OK -> {os.path.join(OUT, CASTELLATED_NAME + '.kicad_mod')}")


if __name__ == "__main__":
    main()
