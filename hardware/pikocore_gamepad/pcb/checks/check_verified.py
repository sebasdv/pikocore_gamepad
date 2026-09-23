#!/usr/bin/env python3
"""G-0: falla mientras queden constantes fisicas sin verificar.

Esta puerta bloquea la generacion de archivos de fabricacion, no el avance
del esquematico ni del layout: se puede iterar el diseno entero con valores
provisionales, pero no se puede mandar a fabricar con ellos.

Uso:  python checks/check_verified.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def pendientes(all_params):
    """Nombres de las constantes que todavia no estan verificadas."""
    return sorted(n for n, p in all_params.items() if not p.verified)


def footprints_provisionales():
    """{constante: motivo} de los footprints que estan puestos para que el
    flujo corra, no porque sean los definitivos.

    Un footprint provisional que llega a fabricacion es una placa donde la
    pieza no entra, asi que bloquea igual que un valor sin medir.
    """
    try:
        import netlist
    except ModuleNotFoundError:
        return {}
    return dict(getattr(netlist, "FOOTPRINTS_PROVISIONALES", {}))


def main():
    import params
    pend = pendientes(params.ALL)
    fps = footprints_provisionales()
    if not pend and not fps:
        print("OK: todas las constantes fisicas y los footprints estan "
              "verificados.")
        return 0

    print(f"BLOQUEADO: {len(pend)} constante(s) sin verificar, "
          f"{len(fps)} footprint(s) provisional(es).\n")
    for n in pend:
        p = params.ALL[n]
        print(f"  [{p.gate}] {n} = {p.value}")
        print(f"        {p.note}\n")
    for n, motivo in sorted(fps.items()):
        print(f"  [FP] {n}")
        print(f"        {motivo}\n")
    print("Medir/confirmar, actualizar params.py y netlist.py, y poner "
          "verified=True / vaciar FOOTPRINTS_PROVISIONALES.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
