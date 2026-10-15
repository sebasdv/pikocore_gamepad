import unittest

import params
from checks import check_verified


class TestParams(unittest.TestCase):

    def test_todo_param_tiene_los_cuatro_campos(self):
        for name, p in params.ALL.items():
            self.assertIsInstance(p.value, float, f"{name}: value debe ser float")
            self.assertIsInstance(p.verified, bool, f"{name}: verified debe ser bool")
            self.assertTrue(p.note, f"{name}: note no puede estar vacia")
            self.assertTrue(p.gate, f"{name}: gate no puede estar vacia")

    def test_la_placa_mide_100_por_60(self):
        # Disposicion estilo Game Boy Micro (spec 2026-10-15): el alto baja
        # de 80 a 60; el ancho no cambia.
        self.assertEqual(params.v("BOARD_W"), 100.0)
        self.assertEqual(params.v("BOARD_H"), 60.0)

    def test_las_constantes_del_panel_estan_declaradas(self):
        for name in ("PANEL_BL_W", "PANEL_BL_H", "PANEL_AA", "PANEL_AA_OFF_X",
                     "PANEL_AA_OFF_TOP", "PANEL_FPC_W", "PANEL_FPC_LEN",
                     "LCD_FPC_PIN_ORDER"):
            self.assertIn(name, params.ALL)

    def test_las_cotas_del_panel_salen_del_datasheet(self):
        # Drawing rev C del DM-TFT13-377 de 24 pines. Cierran por aritmetica:
        # BL - AA = 2 x margen en el lado corto.
        for name in ("PANEL_BL_W", "PANEL_BL_H", "PANEL_AA", "PANEL_AA_OFF_X",
                     "PANEL_AA_OFF_TOP"):
            self.assertTrue(params.ALL[name].verified, name)
        self.assertAlmostEqual(
            params.v("PANEL_BL_W") - 2 * params.v("PANEL_AA_OFF_X"),
            params.v("PANEL_AA"), places=4)

    def test_la_franja_del_fpc_es_la_mas_ancha(self):
        # 29.22 - 23.40 - 1.56 = 4.26: del lado del FPC esta el driver.
        franja = (params.v("PANEL_BL_H") - params.v("PANEL_AA")
                  - params.v("PANEL_AA_OFF_TOP"))
        self.assertAlmostEqual(franja, 4.26, places=3)
        self.assertGreater(franja, params.v("PANEL_AA_OFF_TOP"))

    def test_el_orden_de_pines_del_fpc_queda_sin_verificar(self):
        # No se puede cerrar con el datasheet: depende de que cara del FPC
        # lleva los contactos. Bloquea G-0 hasta medir con el panel en mano.
        self.assertFalse(params.ALL["LCD_FPC_PIN_ORDER"].verified)


class TestAccesorV(unittest.TestCase):
    """params.v() lo consumen gen_fp.py y placements.py. Su unico motivo de
    existir es fallar fuerte ante un typo, asi que ese es el comportamiento
    que hay que fijar."""

    def test_devuelve_el_valor_de_la_constante(self):
        self.assertAlmostEqual(params.v("PANEL_AA"), 23.40, places=4)

    def test_falla_fuerte_con_un_nombre_desconocido(self):
        # Sin esto, un typo devolveria None y se propagaria silencioso a la
        # geometria del footprint.
        with self.assertRaises(KeyError):
            params.v("LCD_BOARD_WIDTH")


class TestCheckVerified(unittest.TestCase):

    def test_reporta_los_no_verificados(self):
        # Con un Param falso, para no depender de cuales queden sin
        # verificar en el proyecto real.
        from params import Param
        falso = {"OK": Param(1.0, True, "medido", "V-0"),
                 "PENDIENTE": Param(2.0, False, "sin medir", "V-9")}
        pend = check_verified.pendientes(falso)
        self.assertEqual(pend, ["PENDIENTE"])

    def test_hoy_queda_exactamente_uno_pendiente(self):
        # G-0 en rojo a proposito: el orden de pines del FPC del panel se
        # verifica con la pieza, no con el datasheet. gen_fab.py se niega
        # sin --force hasta entonces, que es lo que se quiere.
        self.assertEqual(check_verified.pendientes(params.ALL),
                         ["LCD_FPC_PIN_ORDER"])

    def test_pasa_cuando_todo_esta_verificado(self):
        from params import Param
        todos_ok = {"X": Param(1.0, True, "medido", "V-0")}
        self.assertEqual(check_verified.pendientes(todos_ok), [])


if __name__ == "__main__":
    unittest.main()
