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

    LCD7_DEL_DIBUJO = ("LCD7_BOARD_W", "LCD7_BOARD_H", "LCD7_PIN1_X",
                       "LCD7_PIN_PITCH", "LCD7_PIN_PAD", "LCD7_AA",
                       "LCD7_AA_OFF_X", "LCD7_AA_OFF_TOP", "LCD7_HOLE_DIA",
                       "LCD7_HOLE_INSET")
    LCD7_A_MEDIR = ("LCD7_PIN_ROW_TO_EDGE", "LCD7_PIN_DRILL")

    def test_no_quedan_las_constantes_del_panel_de_24_pines(self):
        self.assertNotIn("LCD_FPC_PIN_ORDER", params.ALL)
        self.assertEqual([n for n in params.ALL if n.startswith("PANEL_")], [])

    def test_las_cotas_del_modulo_salen_del_dibujo_del_fabricante(self):
        for name in self.LCD7_DEL_DIBUJO:
            self.assertTrue(params.ALL[name].verified, name)

    def test_las_dos_cotas_que_el_dibujo_no_da_quedan_sin_verificar(self):
        self.assertAlmostEqual(params.v("LCD7_PIN_ROW_TO_EDGE"), 1.27, places=4)
        self.assertAlmostEqual(params.v("LCD7_PIN_DRILL"), 1.0, places=4)
        for name in self.LCD7_A_MEDIR:
            self.assertFalse(params.ALL[name].verified, name)

    def test_los_pines_quedan_centrados_en_el_ancho(self):
        # 6.27 + 6 x 2.54 + 6.27 = 27.78 exacto.
        self.assertAlmostEqual(
            2 * params.v("LCD7_PIN1_X") + 6 * params.v("LCD7_PIN_PITCH"),
            params.v("LCD7_BOARD_W"), places=4)

    def test_el_area_activa_queda_centrada_en_el_ancho(self):
        self.assertAlmostEqual(
            2 * params.v("LCD7_AA_OFF_X") + params.v("LCD7_AA"),
            params.v("LCD7_BOARD_W"), places=4)


class TestPlaca(unittest.TestCase):

    def test_la_placa_mide_100_por_60(self):
        self.assertEqual(params.v("BOARD_W"), 100.0)
        self.assertEqual(params.v("BOARD_H"), 60.0)


class TestAccesorV(unittest.TestCase):
    """params.v() lo consumen gen_fp.py y placements.py. Su unico motivo de
    existir es fallar fuerte ante un typo, asi que ese es el comportamiento
    que hay que fijar."""

    def test_devuelve_el_valor_de_la_constante(self):
        self.assertAlmostEqual(params.v("LCD7_AA"), 23.40, places=4)

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

    def test_hoy_quedan_exactamente_las_dos_medidas_del_modulo(self):
        # G-0 en rojo a proposito: el eje de pines al borde y el diametro de
        # los pines no salen del dibujo, se miden con el modulo en mano.
        # gen_fab.py se niega sin --force hasta entonces.
        self.assertEqual(check_verified.pendientes(params.ALL),
                         ["LCD7_PIN_DRILL", "LCD7_PIN_ROW_TO_EDGE"])

    def test_pasa_cuando_todo_esta_verificado(self):
        from params import Param
        todos_ok = {"X": Param(1.0, True, "medido", "V-0")}
        self.assertEqual(check_verified.pendientes(todos_ok), [])


if __name__ == "__main__":
    unittest.main()
