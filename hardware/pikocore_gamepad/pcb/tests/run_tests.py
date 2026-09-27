#!/usr/bin/env python3
"""Descubre y corre todos los tests de pcb/ con unittest de la stdlib.

pytest NO esta instalado en este entorno y este runner no lo necesita.

Uso:  python tests/run_tests.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.dirname(HERE)

# Documenta el contrato de imports de los tests: "import params",
# "import dxf_io", "from checks import check_verified". Es tecnicamente
# redundante —TestLoader.discover() ya inserta top_level_dir en sys.path—
# pero se deja explicito para que el contrato no dependa de un detalle
# interno de unittest.
sys.path.insert(0, PCB)

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=HERE, pattern="test_*.py", top_level_dir=PCB)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
