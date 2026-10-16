import unittest

import pinmap


class TestPinmap(unittest.TestCase):

    def test_ningun_gpio_esta_asignado_dos_veces(self):
        gpios = [g for g in pinmap.GPIO.keys()]
        self.assertEqual(len(gpios), len(set(gpios)))

    def test_ninguna_funcion_esta_asignada_dos_veces(self):
        funcs = [f for f in pinmap.GPIO.values()]
        self.assertEqual(len(funcs), len(set(funcs)),
                         f"funcion duplicada en {sorted(funcs)}")

    def test_solo_usa_gpios_que_el_modulo_expone(self):
        # RP2350-Plus expone GP0-GP22 y GP26-GP28. GP23/24/25 son internos
        # (MODE del buck-boost, sensado de VBUS, LED) y GP29 no sale al header.
        for g in pinmap.GPIO:
            self.assertTrue(0 <= g <= 22 or 26 <= g <= 28,
                            f"GP{g} no esta expuesto en el header")

    def test_lrck_es_bck_mas_uno(self):
        # El programa PIO de src/audio/i2s.pio genera LRCK en BCK+1 por
        # hardware. Si esto se rompe, el DAC recibe basura y no hay forma de
        # arreglarlo por firmware.
        bck = pinmap.gpio_of("I2S_BCK")
        lrck = pinmap.gpio_of("I2S_LRCK")
        self.assertEqual(lrck, bck + 1)

    def test_spi0_usa_pines_validos_para_spi0(self):
        self.assertIn(pinmap.gpio_of("LCD_SCK"), pinmap.SPI0_SCK_OK)
        self.assertIn(pinmap.gpio_of("LCD_MOSI"), pinmap.SPI0_TX_OK)

    def test_midi_usa_los_dos_pines_libres_del_modulo(self):
        # El modulo expone GP0-22 y GP26-28; GP27/28 eran los unicos libres.
        self.assertEqual(pinmap.GPIO[28], "MIDI_TX")
        self.assertEqual(pinmap.GPIO[27], "MIDI_RX")
        self.assertEqual(pinmap.FREE, ())

    def test_midi_tx_es_un_pin_tx_de_uart0(self):
        self.assertIn(pinmap.gpio_of("MIDI_TX"), pinmap.UART0_TX_OK)

    def test_los_libres_no_chocan_con_los_asignados(self):
        self.assertEqual(set(pinmap.FREE) & set(pinmap.GPIO.keys()), set())

    def test_no_queda_ningun_gpio_expuesto_sin_declarar(self):
        # Todo pin del header tiene que estar o asignado o explicitamente
        # libre. Un pin que no aparezca en ninguno de los dos lados es un
        # olvido, no una decision.
        expuestos = set(range(0, 23)) | {26, 27, 28}
        declarados = set(pinmap.GPIO) | set(pinmap.FREE)
        self.assertEqual(expuestos - declarados, set(),
                         "GPIO expuestos sin declarar")

    def test_el_pin_fisico_del_header_se_deriva_bien(self):
        # GP0 es el pin 1 del header tipo Pico; GP22 es el pin 29.
        self.assertEqual(pinmap.header_pin(0), 1)
        self.assertEqual(pinmap.header_pin(22), 29)
        self.assertEqual(pinmap.header_pin(28), 34)

    def test_cada_gpio_asignado_cae_en_un_pin_distinto_del_header(self):
        pines = [pinmap.header_pin(g) for g in pinmap.GPIO]
        self.assertEqual(len(pines), len(set(pines)))

    def test_pedir_una_funcion_inexistente_falla_fuerte(self):
        with self.assertRaises(KeyError):
            pinmap.gpio_of("NO_EXISTE")


class TestCheckPinmap(unittest.TestCase):

    def test_parsea_los_defines_de_un_config_h(self):
        from checks import check_pinmap
        src = """
        #define PIN_LCD_SCK   2   // pin 4
        #define PIN_LCD_MOSI  3
        #define AUDIO_SAMPLE_RATE 44100
        """
        d = check_pinmap.parse_defines(src)
        self.assertEqual(d["PIN_LCD_SCK"], 2)
        self.assertEqual(d["PIN_LCD_MOSI"], 3)

    def test_ignora_los_defines_que_no_son_pines(self):
        from checks import check_pinmap
        d = check_pinmap.parse_defines("#define AUDIO_SAMPLE_RATE 44100")
        self.assertNotIn("AUDIO_SAMPLE_RATE", d)

    def test_ignora_los_defines_que_no_son_enteros(self):
        # DISP_SPI_SPEED (62500000) y PCF_ADDR_BTN 0x20 conviven en el mismo
        # archivo; ninguno es un numero de pin.
        from checks import check_pinmap
        d = check_pinmap.parse_defines(
            "#define DISP_SPI_SPEED (62500000)\n#define PCF_ADDR_BTN 0x20\n")
        self.assertEqual(d, {})

    def test_detecta_una_discrepancia(self):
        from checks import check_pinmap
        diffs = check_pinmap.compare({"LCD_SCK": 2}, {"PIN_LCD_SCK": 9})
        self.assertEqual(len(diffs), 1)
        self.assertIn("LCD_SCK", diffs[0])

    def test_detecta_una_funcion_ausente_en_el_firmware(self):
        from checks import check_pinmap
        diffs = check_pinmap.compare({"LCD_SCK": 2}, {})
        self.assertEqual(len(diffs), 1)

    def test_no_reporta_nada_cuando_coinciden(self):
        from checks import check_pinmap
        self.assertEqual(check_pinmap.compare({"LCD_SCK": 2}, {"PIN_LCD_SCK": 2}), [])

    def test_detecta_un_pin_del_firmware_que_la_pcb_no_conoce(self):
        # La direccion inversa: si alguien parte del config.h de V1, quedan
        # PIN_BTN_PLAY, PIN_ENC0_A y demas apuntando a hardware que V2 no
        # tiene. Sin este chequeo el firmware compila y lee pines muertos.
        from checks import check_pinmap
        sobra = check_pinmap.sobrantes({"LCD_SCK": 2},
                                       {"PIN_LCD_SCK": 2, "PIN_ENC0_A": 9})
        self.assertEqual(sobra, ["PIN_ENC0_A"])

    def test_no_reporta_sobrantes_cuando_coinciden(self):
        from checks import check_pinmap
        self.assertEqual(
            check_pinmap.sobrantes({"LCD_SCK": 2}, {"PIN_LCD_SCK": 2}), [])


class TestFirmwareStubs(unittest.TestCase):
    """src/hw_gamepi13.h elige pines SOLO de firmware (LED, stubs de clock y
    trigger) con numeros literales que G-4 no ve: G-4 lee config.h. Si uno
    de esos literales cae en un GPIO que la placa ya usa, compila y se
    descubre al enchufar."""

    def _bloque_gamepad(self):
        import os, re
        raiz = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            "..", "..", "..", ".."))
        txt = open(os.path.join(raiz, "src", "hw_gamepi13.h"), encoding="utf-8").read()
        ini = txt.index("#if PIKO_GAMEPAD")
        bloque = txt[ini:txt.index(chr(10) + "#else", ini)]   # la rama GamePi13 no cuenta
        return dict(re.findall(r"#define\s+(GAMEPI_\w+_PIN)\s+(-?\d+)", bloque))

    def test_los_pines_solo_de_firmware_no_pisan_la_placa(self):
        # -1 = sin pin, el firmware lo salta. 25 = LED onboard del modulo, que
        # no sale al header. Cualquier otro numero pisaria un GPIO de la placa
        # (GP27/28 son MIDI_RX/MIDI_TX).
        pines = self._bloque_gamepad()
        self.assertTrue(pines, "no se encontro ningun GAMEPI_*_PIN literal")
        for nombre, n in pines.items():
            self.assertIn(int(n), (-1, 25),
                          f"{nombre} = {n}: solo -1 (sin pin) o 25 (LED del modulo)")


if __name__ == "__main__":
    unittest.main()
