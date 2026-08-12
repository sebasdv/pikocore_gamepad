#!/usr/bin/env python3
"""Genera los footprints propios en lib/gamesetup_fp.pretty.

Python puro, sin pcbnew: escribe los .kicad_mod como texto. Eso permite
testear la geometria con unittest sin levantar KiCad, que es donde estan los
errores caros — un pad corrido no lo ve nadie hasta que la placa llega.

Toda cota fisica sale de params.py, nunca de un numero suelto aca.

Footprints:
  - LCD_ST7789_240x240_7P : el modulo de 1.3 pulgadas, header macho soldado
                            directo, con la ventana del panel en Cmts.User
                            para que el usuario la use de guia en Rhino.
  - RP2350-Plus_Socket    : se copia de V1 sin cambios de geometria.

ORIGEN del footprint del LCD = PAD 1 (GND). Es el mismo criterio que V1 usaba
con el OLED: la tabla PLACEMENTS habla de origenes de footprint, y tener el
origen en un pad hace que la posicion sea verificable con una regla sobre la
placa impresa.
"""
import os
import uuid as uuidlib

import params

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "lib", "gamesetup_fp.pretty")

LCD_PIN_NAMES = ["GND", "VCC", "SCL", "SDA", "RES", "DC", "BLK"]

# Header macho de 2.54: poste de 0.64mm de lado. 1.0 de taladro deja pasar la
# diagonal (0.9mm) con margen; 1.7 de pad da un anillo de 0.35mm por lado.
LCD_PAD_DRILL = 1.0
LCD_PAD_SIZE = 1.7


def u():
    return str(uuidlib.uuid4())


def F(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


# ---------------------------------------------------------------- geometria
# Todo se expresa relativo al PAD 1, que es el origen del footprint.
# En coordenadas del modulo (esquina superior izquierda = 0,0) el pad 1 esta
# en (LCD_PIN1_X, LCD_PIN_ROW_Y); restar ese offset lleva todo al origen.

def _origin_offset():
    return params.v("LCD_PIN1_X"), params.v("LCD_PIN_ROW_Y")


def lcd_pads():
    """Los 7 pads del header, con el pad 1 en (0, 0)."""
    pitch = params.v("LCD_PIN_PITCH")
    return [
        {"num": i + 1, "name": LCD_PIN_NAMES[i], "x": i * pitch, "y": 0.0,
         "drill": LCD_PAD_DRILL, "size": LCD_PAD_SIZE}
        for i in range(7)
    ]


def lcd_outline():
    """Contorno del modulo, relativo al pad 1."""
    ox, oy = _origin_offset()
    return {"x0": -ox, "y0": -oy,
            "x1": params.v("LCD_BOARD_W") - ox,
            "y1": params.v("LCD_BOARD_H") - oy}


def lcd_holes():
    """Los 4 agujeros de montaje, relativos al pad 1."""
    ox, oy = _origin_offset()
    inset = params.v("LCD_HOLE_INSET")
    dia = params.v("LCD_HOLE_DIA")
    xs = [inset - ox, params.v("LCD_BOARD_W") - inset - ox]
    ys = [inset - oy, params.v("LCD_BOARD_H") - inset - oy]
    return [{"x": x, "y": y, "drill": dia} for y in ys for x in xs]


def lcd_window():
    """Ventana del panel (area activa), relativa al pad 1. Va a Cmts.User:
    es la guia de recorte de la tapa del enclosure, no cobre."""
    ox, oy = _origin_offset()
    w = params.v("LCD_ACTIVE_W")
    # El area activa esta centrada en el ancho del modulo.
    x0 = (params.v("LCD_BOARD_W") - w) / 2 - ox
    y0 = params.v("LCD_ACTIVE_TOP") - oy
    return {"x0": x0, "y0": y0, "x1": x0 + w, "y1": y0 + w}


# ---------------------------------------------------------------- escritura

def _pad_thru(num, name, x, y, drill, size, shape="circle"):
    return (f'  (pad "{num}" thru_hole {shape} (at {F(x)} {F(y)}) '
            f'(size {F(size)} {F(size)}) (drill {F(drill)}) '
            f'(layers "*.Cu" "*.Mask") (pinfunction "{name}") '
            f'(uuid "{u()}"))\n')


def _npth(x, y, drill):
    return (f'  (pad "" np_thru_hole circle (at {F(x)} {F(y)}) '
            f'(size {F(drill)} {F(drill)}) (drill {F(drill)}) '
            f'(layers "F&B.Cu" "*.Mask") (uuid "{u()}"))\n')


def _line(layer, x0, y0, x1, y1, w=0.12):
    return (f'  (fp_line (start {F(x0)} {F(y0)}) (end {F(x1)} {F(y1)}) '
            f'(stroke (width {F(w)}) (type solid)) (layer "{layer}") '
            f'(uuid "{u()}"))\n')


def _box(layer, x0, y0, x1, y1, w=0.12):
    return (_line(layer, x0, y0, x1, y0, w) + _line(layer, x1, y0, x1, y1, w) +
            _line(layer, x1, y1, x0, y1, w) + _line(layer, x0, y1, x0, y0, w))


def build_lcd():
    name = "LCD_ST7789_240x240_7P"
    c, win = lcd_outline(), lcd_window()
    out = [
        f'(footprint "{name}"\n',
        '  (version 20240108)\n',
        '  (generator "gen_fp.py")\n',
        '  (layer "F.Cu")\n',
        '  (attr through_hole)\n',
        '  (descr "Modulo IPS 1.3in 240x240 ST7789, 7 pines. Header macho '
        'soldado directo. Origen = pad 1 (GND). Cotas de GAMESETUP/layout.png '
        'via params.py. El rectangulo interior de Cmts.User es el area activa: '
        'es lo que hay que recortar en la tapa del enclosure.")\n',
        f'  (property "Reference" "J**" (at 0 -3 0) (layer "F.SilkS") '
        f'(uuid "{u()}") (effects (font (size 1 1) (thickness 0.15))))\n',
        f'  (property "Value" "{name}" (at 0 -5 0) (layer "F.Fab") '
        f'(uuid "{u()}") (effects (font (size 1 1) (thickness 0.15))))\n',
    ]
    for p in lcd_pads():
        out.append(_pad_thru(p["num"], p["name"], p["x"], p["y"],
                             p["drill"], p["size"],
                             "rect" if p["num"] == 1 else "circle"))
    for h in lcd_holes():
        out.append(_npth(h["x"], h["y"], h["drill"]))
    # Contorno del modulo en Fab (documentacion) y en Cmts (guia para Rhino).
    out.append(_box("F.Fab", c["x0"], c["y0"], c["x1"], c["y1"]))
    out.append(_box("Cmts.User", c["x0"], c["y0"], c["x1"], c["y1"]))
    out.append(_box("Cmts.User", win["x0"], win["y0"], win["x1"], win["y1"], 0.2))
    out.append(')\n')
    return "".join(out)


def copiar_socket_de_v1():
    """El socket 2x20 del RP2350-Plus se reusa tal cual de V1.

    Solo se cambia la ruta del modelo 3D a la libreria de este proyecto: la
    geometria de pads no se toca, porque ya esta verificada contra el modulo
    fisico.
    """
    src = os.path.join(HERE, "..", "..", "NEWSETUP", "pcb", "lib",
                       "newsetup_fp.pretty", "RP2350-Plus_Socket.kicad_mod")
    dst = os.path.join(OUT, "RP2350-Plus_Socket.kicad_mod")
    if not os.path.isfile(src):
        print(f"AVISO: no se encontro {src}")
        return False
    with open(src, encoding="utf-8") as f:
        s = f.read()
    s = s.replace("newsetup_fp.3dshapes", "gamesetup_fp.3dshapes")
    s = s.replace("/NEWSETUP/pcb/lib/", "/lib/")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(s)
    return True


def main():
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "LCD_ST7789_240x240_7P.kicad_mod")
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_lcd())
    print(f"OK -> {path}")
    if copiar_socket_de_v1():
        print(f"OK -> {os.path.join(OUT, 'RP2350-Plus_Socket.kicad_mod')} "
              f"(copiado de V1)")


if __name__ == "__main__":
    main()
