#!/usr/bin/env python3
"""Genera los footprints propios en lib/gamesetup_fp.pretty.

Python puro, sin pcbnew: escribe los .kicad_mod como texto. Eso permite
testear la geometria con unittest sin levantar KiCad, que es donde estan los
errores caros — un pad corrido no lo ve nadie hasta que la placa llega.

Toda cota fisica sale de params.py, nunca de un numero suelto aca.

Footprints:
  - LCD_LH133T_24P     : el panel desnudo de 1.3 pulgadas (sin pads: solo
                         contorno, area activa y cola del FPC en Cmts.User,
                         para el enclosure y para Rhino). El conector del FPC
                         es una pieza aparte, importada de LCSC.
  - RP2350-Plus_Castellated : el modulo se suelda plano al dorso por sus
                         castellations; se deriva de la huella oficial de la
                         Pico (KiCad), sin agujeros de montaje ni pads D1-D3.

ORIGEN del footprint del panel = centro del AREA ACTIVA: es lo que se mide
sobre la placa impresa y lo que decide la ergonomia.
"""
import os
import uuid as uuidlib

import params

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "lib", "gamesetup_fp.pretty")

PANEL_NAME = "LCD_LH133T_24P"


def u():
    return str(uuidlib.uuid4())


def F(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


# ---------------------------------------------------------------- geometria
# ORIGEN del footprint del panel = CENTRO DEL AREA ACTIVA. El panel no tiene
# pads (es una pieza pegada; lo electrico va por el conector J4), asi que el
# punto que importa para colocarlo es donde queda la imagen. placements.py
# habla de ese centro, que es lo que se mide sobre la placa impresa.
#
# El FPC sale hacia +Y (abajo en la placa): la franja del driver (4.26) queda
# del lado +Y y el margen chico (1.56) del lado -Y.

def panel_outline():
    """Contorno del backlight (BL), relativo al centro del area activa."""
    a = params.v("PANEL_AA") / 2
    top = -a - params.v("PANEL_AA_OFF_TOP")
    return {"x0": -a - params.v("PANEL_AA_OFF_X"),
            "x1": a + params.v("PANEL_AA_OFF_X"),
            "y0": top,
            "y1": top + params.v("PANEL_BL_H")}


def panel_window():
    """Area activa, centrada en el origen. Va a Cmts.User: es la ventana a
    recortar en la tapa del enclosure (el datasheet pide 0.5mm mas por lado)."""
    a = params.v("PANEL_AA") / 2
    return {"x0": -a, "y0": -a, "x1": a, "y1": a}


def panel_fpc():
    """Cola del FPC desplegada, saliendo por el borde +Y, centrada en X. Solo
    documentacion (Cmts.User): dice hasta donde llega el flex y donde tiene
    que estar el conector. Se asume centrada en el ancho del panel, que es
    como la dibuja el datasheet (aproximado: +-1mm no cambia nada, el flex
    tiene holgura)."""
    c = panel_outline()
    w = params.v("PANEL_FPC_W") / 2
    return {"x0": -w, "y0": c["y1"], "x1": w,
            "y1": c["y1"] + params.v("PANEL_FPC_LEN")}


# ---------------------------------------------------------------- escritura

def _line(layer, x0, y0, x1, y1, w=0.12):
    return (f'  (fp_line (start {F(x0)} {F(y0)}) (end {F(x1)} {F(y1)}) '
            f'(stroke (width {F(w)}) (type solid)) (layer "{layer}") '
            f'(uuid "{u()}"))\n')


def _box(layer, x0, y0, x1, y1, w=0.12):
    return (_line(layer, x0, y0, x1, y0, w) + _line(layer, x1, y0, x1, y1, w) +
            _line(layer, x1, y1, x0, y1, w) + _line(layer, x0, y1, x0, y0, w))


def build_panel():
    name = PANEL_NAME
    c, win, fpc = panel_outline(), panel_window(), panel_fpc()
    m = 0.25   # courtyard: margen de colocacion alrededor del vidrio
    out = [
        f'(footprint "{name}"\n',
        '  (version 20240108)\n',
        '  (generator "gen_fp.py")\n',
        '  (layer "F.Cu")\n',
        # Fuera del CPL (la pega el usuario) pero DENTRO del BOM: hay que
        # comprarla. Si dijera exclude_from_bom, el DRC con --schematic-parity
        # lo reporta contra el simbolo, que la lista.
        '  (attr smd exclude_from_pos_files)\n',
        '  (descr "Panel IPS 1.3in 240x240 ST7789VW desnudo, DisplayModule '
        'DM-TFT13-377 de 24 pines (LH133T-IF05). SIN pads: se pega al frente '
        'y el FPC de 24P/0.5mm baja al conector J4. Origen = centro del area '
        'activa. El rectangulo interior de Cmts.User es el area activa (la '
        'ventana del enclosure, +0.5mm por lado); el saliente de abajo es la '
        'cola del FPC desplegada. Cotas del datasheet via params.py.")\n',
        f'  (property "Reference" "LCD**" (at 0 {F(c["y0"] - 1.5)} 0) '
        f'(layer "F.SilkS") (uuid "{u()}") '
        '(effects (font (size 1 1) (thickness 0.15))))\n',
        f'  (property "Value" "{name}" (at 0 0 0) (layer "F.Fab") '
        f'(uuid "{u()}") (effects (font (size 1 1) (thickness 0.15))))\n',
    ]
    out.append(_box("F.Fab", c["x0"], c["y0"], c["x1"], c["y1"]))
    out.append(_box("F.CrtYd", c["x0"] - m, c["y0"] - m, c["x1"] + m,
                    c["y1"] + m, 0.05))
    out.append(_box("Cmts.User", c["x0"], c["y0"], c["x1"], c["y1"]))
    out.append(_box("Cmts.User", win["x0"], win["y0"], win["x1"], win["y1"], 0.2))
    out.append(_box("Cmts.User", fpc["x0"], fpc["y0"], fpc["x1"], fpc["y1"]))
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
#
# El conector del FPC del panel (XUNPU FPC-05FB-24PH20, LCSC C2856831)
# tampoco se genera aca: se importo con easyeda2kicad a gamesetup_lcsc, con
# el modelo 3D reapuntado a ${KIPRJMOD}/lib/gamesetup_lcsc.3dshapes/.


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
    de depuracion D1-D3. Quedan los pads 1-40 y los auxiliares sin nombre."""
    if not os.path.isfile(PICO_SMD_HAND):
        print(f"AVISO: no se encontro {PICO_SMD_HAND}")
        return False
    with open(PICO_SMD_HAND, encoding="utf-8", newline="") as f:
        s = f.read()

    def quitar(bloque):
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
    path = os.path.join(OUT, PANEL_NAME + ".kicad_mod")
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_panel())
    print(f"OK -> {path}")
    if derivar_modulo_castellated():
        print(f"OK -> {os.path.join(OUT, CASTELLATED_NAME + '.kicad_mod')}")


if __name__ == "__main__":
    main()
