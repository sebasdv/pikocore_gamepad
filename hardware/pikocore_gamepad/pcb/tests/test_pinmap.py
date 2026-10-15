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

    def test_solo_usa_gpios_que_existen_en_el_rp2350a(self):
        # Chip-down: los 30 GPIO del RP2350A (QFN-60) estan disponibles.
        for g in pinmap.GPIO:
            self.assertTrue(0 <= g <= 29, f"GP{g} no existe en el RP2350A")

    def test_el_pinmap_del_firmware_no_se_movio_con_el_chip_down(self):
        # El cambio de modulo a chip-down no puede mover ninguna funcion que
        # el firmware ya usa: GP0-GP22 y GP26 quedan exactamente igual.
        esperado = {0: "DPAD_UP", 2: "LCD_SCK", 8: "I2S_DIN", 16: "I2S_BCK",
                    17: "I2S_LRCK", 22: "DAC_XSMT", 26: "LCD_TE"}
        for g, f in esperado.items():
            self.assertEqual(pinmap.GPIO[g], f)

    def test_los_gpio_que_eran_internos_del_modulo_hacen_lo_mismo(self):
        # GP23/24/29 hacian, DENTRO del modulo, modo del regulador, sensado
        # de VBUS y VSYS/3. En la placa hacen lo mismo.
        self.assertEqual(pinmap.GPIO[23], "BB_PS")
        self.assertEqual(pinmap.GPIO[24], "VBUS_SENSE")
        self.assertEqual(pinmap.GPIO[29], "VSYS_ADC")

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

    def test_quedan_exactamente_tres_pines_libres(self):
        # GP27/28 (con ADC, stubs de clock/trigger en el firmware) y GP25
        # (era el LED del modulo).
        self.assertEqual(sorted(pinmap.FREE), [25, 27, 28])

    def test_los_libres_no_chocan_con_los_asignados(self):
        self.assertEqual(set(pinmap.FREE) & set(pinmap.GPIO.keys()), set())

    def test_no_queda_ningun_gpio_expuesto_sin_declarar(self):
        # Todo GPIO tiene que estar o asignado o explicitamente libre. Un
        # pin que no aparezca en ninguno de los dos lados es un olvido, no
        # una decision.
        expuestos = set(range(0, 30))
        declarados = set(pinmap.GPIO) | set(pinmap.FREE)
        self.assertEqual(expuestos - declarados, set(),
                         "GPIO expuestos sin declarar")

    def test_quedan_dos_pines_con_adc_libres(self):
        # GP26-29 tienen ADC. GP26 es LCD_TE y GP29 VSYS/3; GP27/28 siguen
        # libres (el firmware los usa como stubs de clock/trigger).
        for g in (27, 28):
            self.assertIn(g, pinmap.FREE)
        self.assertEqual(pinmap.gpio_of("LCD_TE"), 26)

    def test_el_pin_del_qfn_se_deriva_bien(self):
        # Contra la tabla verificada del RP2350A: GPIO0 = pin 2, GPIO22 =
        # pin 34, GPIO29 = pin 43.
        self.assertEqual(pinmap.qfn_pin(0), 2)
        self.assertEqual(pinmap.qfn_pin(22), 34)
        self.assertEqual(pinmap.qfn_pin(29), 43)

    def test_la_tabla_del_qfn_tiene_los_61_pads(self):
        self.assertEqual(sorted(pinmap.RP2350A_PINS), list(range(1, 62)))
        gpios = [n for n in pinmap.RP2350A_PINS.values() if n.startswith("GPIO")]
        self.assertEqual(len(gpios), 30)

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


if __name__ == "__main__":
    unittest.main()
