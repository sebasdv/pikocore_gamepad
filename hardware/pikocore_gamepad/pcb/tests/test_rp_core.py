import unittest

import import_rp_minimal as imp
import pinmap
import rp_core
import rp_core_ref as R


class TestRecorte(unittest.TestCase):

    def test_segmento_adentro_no_cambia(self):
        self.assertEqual(imp.recortar(-1, 0, 1, 0, r=2), (-1, 0, 1, 0))

    def test_segmento_que_sale_se_corta_en_el_borde(self):
        self.assertEqual(imp.recortar(-3.4, -1.2, -11.2, -1.2, r=7.5),
                         (-3.4, -1.2, -7.5, -1.2))

    def test_diagonal_se_corta_en_el_borde(self):
        x0, y0, x1, y1 = imp.recortar(0, 0, 10, 10, r=5)
        self.assertAlmostEqual(x1, 5)
        self.assertAlmostEqual(y1, 5)

    def test_segmento_afuera_se_descarta(self):
        self.assertIsNone(imp.recortar(8, 0, 9, 0, r=7.5))


class TestFanout(unittest.TestCase):

    def test_cada_tramo_cae_dentro_del_radio(self):
        for net, capa, x0, y0, x1, y1, ancho in R.FANOUT:
            for v in (x0, y0, x1, y1):
                self.assertLessEqual(abs(v), imp.FANOUT_R + 1e-6, net)

    def test_nets_traducidas_existen_en_el_pinmap(self):
        usadas = set()
        for net, *_ in R.FANOUT:
            n = rp_core.net_fanout(net)
            if n is not None:
                usadas.add(n)
        funciones = set(pinmap.GPIO.values()) | {"RUN", "SWDIO", "SWCLK"}
        self.assertLessEqual(usadas, funciones)

    def test_las_nets_con_fanout_tienen_tramos(self):
        # Si la placa oficial cambia de pinout, que se note aca y no en el DRC.
        con_tramos = {rp_core.net_fanout(n) for n, *_ in R.FANOUT}
        self.assertLessEqual(rp_core.FANOUT_NETS, con_tramos)

    def test_gpio_libres_no_se_copian(self):
        for g in pinmap.FREE:
            self.assertIsNone(rp_core.net_fanout(f"/GPIO{g}"))


if __name__ == "__main__":
    unittest.main()
