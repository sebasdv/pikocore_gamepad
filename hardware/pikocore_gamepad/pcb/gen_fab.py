#!/usr/bin/env python3
"""Genera el paquete de fabricacion para JLCPCB en fab/.

Correr con el python de KiCad 9, DESPUES de tener la placa ruteada:
  "$LOCALAPPDATA/Programs/KiCad/9.0/bin/python.exe" gen_fab.py

Que produce, todo dentro de fab/:
  gerber/*.g*                 las 4 capas de cobre + mascaras, serigrafias
                              y contorno
  gerber/*.drl                taladros en Excellon, PTH y NPTH por separado
  pikocore_gamepad_BOM.csv    lista de materiales en el formato de JLCPCB
  pikocore_gamepad_CPL.csv    posiciones para el pick-and-place
  pikocore_gamepad_fab.zip    todo lo anterior, listo para subir

G-0 ES UNA PUERTA, NO UN AVISO. Si quedan constantes fisicas sin verificar o
footprints provisionales, el script SE NIEGA a generar nada. Un footprint
provisional que llega a fabricacion es una placa donde la pieza no entra, y
para cuando eso se descubre ya se pago el pedido. Para inspeccionar el paquete
sin cerrar G-0 esta --force, que ademas estampa un aviso en el nombre del zip.

CONVENCIONES DE JLCPCB cableadas aca, que conviene no "corregir":

  - Los gerbers van con extension Protel (.gtl/.gbl/.g2/.g3...), que es lo que
    espera su parser. Por eso NO se pasa --no-protel-ext.
  - El drill va en Excellon, en mm, con PTH y NPTH en archivos separados.
  - Gerbers y drill comparten el mismo origen (--use-drill-file-origin y
    --drill-origin plot). Si no coinciden, los taladros salen corridos
    respecto del cobre y la placa se fabrica mal sin que nada avise.
  - El CPL usa las columnas Designator/Mid X/Mid Y/Layer/Rotation, con esos
    nombres exactos, y Layer en Top/Bottom capitalizado.
  - El BOM usa Comment/Designator/Footprint/LCSC, agrupando en una sola fila
    los designadores que comparten valor y footprint.

QUE NO HACE, a proposito: no elige partes ni inventa codigos LCSC. Los
componentes sin codigo salen con la celda vacia y el script los reporta al
final — hay que completarlos en el portal de JLCPCB o cargarlos en netlist.py.
Inventar un codigo es peor que dejarlo en blanco.
"""
import csv
import json
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from netlist import INSTANCES

PCB = os.path.join(HERE, "pikocore_gamepad.kicad_pcb")
FAB = os.path.join(HERE, "fab")
GERBER = os.path.join(FAB, "gerber")
PROYECTO = "pikocore_gamepad"

# Las 4 de cobre mas lo que hace falta para fabricar: mascaras de soldadura,
# serigrafias, pasta y el contorno. Edge.Cuts NO es opcional: sin el, JLCPCB
# no sabe por donde cortar y rechaza el pedido.
CAPAS = ("F.Cu,GND,PWR,B.Cu,"
         "F.Mask,B.Mask,F.SilkS,B.SilkS,F.Paste,B.Paste,Edge.Cuts")

KICLI = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "KiCad",
                     "9.0", "bin", "kicad-cli.exe")


def _cli(*args):
    """Corre kicad-cli y aborta si falla."""
    r = subprocess.run([KICLI] + list(args), capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        raise SystemExit(f"kicad-cli fallo: {' '.join(args[:3])}")
    return r.stdout


def puerta_g0(force):
    """G-0: no se generan archivos de fabricacion con datos provisionales."""
    from checks.check_verified import pendientes, footprints_provisionales
    import params
    pend = pendientes(params.ALL)
    fps = footprints_provisionales()
    if not pend and not fps:
        print("G-0 OK: constantes y footprints verificados.")
        return True
    print(f"G-0 BLOQUEA: {len(pend)} constante(s) sin verificar, "
          f"{len(fps)} footprint(s) provisional(es).")
    for n in pend:
        print(f"   [{params.ALL[n].gate}] {n}")
    for n in sorted(fps):
        print(f"   [FP] {n}")
    if not force:
        print()
        print("Estos archivos NO se pueden mandar a fabricar. Corregir y "
              "reintentar, o usar --force para inspeccionar el paquete.")
        raise SystemExit(1)
    print("--force: se genera igual, marcado como NO-FABRICABLE.")
    return False


def estado_drc():
    """Reporta el ultimo DRC. Las conexiones abiertas son lo grave.

    No bloquea: las violaciones de margen conocidas (los pads del SOT-563 de
    U2, a 0.15mm por el paso de 0.50) tienen su regla en el .kicad_dru y
    JLCPCB las fabrica sin problema en 4 capas.
    """
    log = os.path.join(HERE, "logs", "drc.json")
    if not os.path.isfile(log):
        print("AVISO: no hay logs/drc.json — no se verifico el DRC.")
        return
    with open(log, encoding="utf-8") as f:
        d = json.load(f)
    u = len(d.get("unconnected_items", []))
    v = len(d.get("violations", []))
    if u:
        print(f"AVISO: el ultimo DRC tenia {u} conexion(es) ABIERTA(S). "
              f"Una placa con nets sin cerrar no funciona.")
    else:
        print(f"DRC: 0 conexiones abiertas, {v} violacion(es) de margen.")


def gerbers():
    os.makedirs(GERBER, exist_ok=True)
    _cli("pcb", "export", "gerbers", "-o", GERBER + os.sep,
         "--layers", CAPAS, "--no-x2", "--subtract-soldermask",
         "--use-drill-file-origin", PCB)
    _cli("pcb", "export", "drill", "-o", GERBER + os.sep,
         "--format", "excellon", "--drill-origin", "plot",
         "--excellon-units", "mm", "--excellon-separate-th",
         "--generate-map", "--map-format", "gerberx2", PCB)
    n = len(os.listdir(GERBER))
    print(f"gerbers + drill: {n} archivos en fab/gerber/")
    return n


def cpl():
    """Posiciones para el pick-and-place.

    Solo SMD: los THT los suelda una persona. Meterlos en el CPL hace que
    JLCPCB los cotice como colocacion automatica que despues no puede hacer.
    """
    tmp = os.path.join(FAB, "_pos.csv")
    _cli("pcb", "export", "pos", "-o", tmp, "--format", "csv",
         "--units", "mm", "--side", "both", "--smd-only",
         "--exclude-dnp", "--use-drill-file-origin", PCB)
    with open(tmp, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    dst = os.path.join(FAB, f"{PROYECTO}_CPL.csv")
    with open(dst, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in filas:
            # KiCad escribe "top"/"bottom"; JLCPCB espera "Top"/"Bottom".
            lado = "Top" if r["Side"].lower().startswith("t") else "Bottom"
            w.writerow([r["Ref"], r["PosX"], r["PosY"], lado, r["Rot"]])
    os.remove(tmp)
    print(f"CPL: {len(filas)} componente(s) SMD -> {os.path.basename(dst)}")
    return len(filas)


def _orden_ref(ref):
    """R10 va despues de R9, no entre R1 y R2."""
    pre = "".join(c for c in ref if c.isalpha())
    num = "".join(c for c in ref if c.isdigit())
    return (pre, int(num) if num else 0)


def bom():
    """BOM en el formato de JLCPCB, agrupado por (valor, footprint, LCSC).

    Se agrupa porque JLCPCB cotiza por LINEA de BOM, no por componente: 25
    condensadores de 100nF son una linea con 25 designadores, no 25 lineas.
    """
    grupos = {}
    for sym, ref, valor, x, y, nets, props in INSTANCES:
        clave = (valor, props.get("FP", ""), props.get("LCSC", ""))
        grupos.setdefault(clave, []).append(ref)

    dst = os.path.join(FAB, f"{PROYECTO}_BOM.csv")
    sin_codigo = []
    with open(dst, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC"])
        for (valor, fp, lcsc), refs in sorted(grupos.items()):
            refs = sorted(refs, key=_orden_ref)
            # El footprint va sin el prefijo de libreria: para JLCPCB es solo
            # una referencia visual del operario.
            w.writerow([valor, ",".join(refs),
                        fp.partition(":")[2] or fp, lcsc])
            if not lcsc:
                sin_codigo.append((valor, len(refs)))
    print(f"BOM: {len(grupos)} linea(s) -> {os.path.basename(dst)}")
    return sin_codigo


def empaquetar(fabricable):
    sufijo = "" if fabricable else "_NO-FABRICABLE"
    dst = os.path.join(FAB, f"{PROYECTO}_fab{sufijo}.zip")
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre in sorted(os.listdir(GERBER)):
            z.write(os.path.join(GERBER, nombre), f"gerber/{nombre}")
        for nombre in (f"{PROYECTO}_BOM.csv", f"{PROYECTO}_CPL.csv"):
            p = os.path.join(FAB, nombre)
            if os.path.isfile(p):
                z.write(p, nombre)
    print(f"zip: {os.path.basename(dst)} "
          f"({os.path.getsize(dst) / 1024:.0f} KB)")
    return dst


def main():
    force = "--force" in sys.argv
    if not os.path.isfile(PCB):
        raise SystemExit(f"FALTA: {PCB}")
    if not os.path.isfile(KICLI):
        raise SystemExit(f"FALTA kicad-cli en {KICLI}")

    fabricable = puerta_g0(force)
    estado_drc()
    print()
    os.makedirs(FAB, exist_ok=True)
    gerbers()
    cpl()
    sin_codigo = bom()
    print()
    empaquetar(fabricable)

    if sin_codigo:
        print()
        print(f"FALTAN {len(sin_codigo)} codigo(s) LCSC — completarlos en el "
              f"portal de JLCPCB o cargarlos en netlist.py:")
        for valor, n in sorted(sin_codigo):
            print(f"   {valor:<14} x{n}")
    if not fabricable:
        print()
        print("RECORDATORIO: el paquete dice NO-FABRICABLE porque G-0 no "
              "cerro. Sirve para inspeccionar, no para pedir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
