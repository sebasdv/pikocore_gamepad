# Game Boy Micro layout (100 × 60) + TRS MIDI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the pikocore_gamepad board on a 100 × 60 mm outline with the Game Boy Micro's horizontal layout and add MIDI IN/OUT on 3.5 mm TRS type A, ending with DRC 0 errors / 0 unconnected / 0 parity.

**Architecture:** Everything is generated from Python: `pinmap.py` → `netlist.py` → `gen_sch.py` (schematic) → `gen_pcb.py` + `placements.py` (board) → `manual_tracks.py` → `plane_vias.py` → `route_io.py` + freerouting → `finish_pcb.py` → DRC. The change is four source files plus their tests, then the routing cycle run until DRC is clean. Nothing is edited in KiCad's GUI.

**Tech Stack:** KiCad 9.0.1 Python (`"/c/Program Files/KiCad/9.0/bin/python.exe"`, called `$KIPY` below), `kicad-cli` 9 (`$KICLI`), freerouting 2.4.1 headless (JAR at `$HOME/Documents/KiCad/10.0/3rdparty/plugins/app_freerouting_kicad-plugin/jar/freerouting-2.4.1.jar`), stdlib `unittest` via `tests/run_tests.py`. Git Bash on Windows.

**Spec:** `docs/superpowers/specs/2026-10-15-pikocore-gamepad-micro-layout-midi-design.md`

## Global Constraints

- Branch `hw/chipdown-rp2350`, on top of commit 251e713. Commit after every task; never push.
- Working directory for every command: `hardware/pikocore_gamepad/pcb`. Set once per shell:
  `KIPY="/c/Program Files/KiCad/9.0/bin/python.exe"; KICLI="/c/Program Files/KiCad/9.0/bin/kicad-cli.exe"`.
- Board outline 100 × 60 mm, 4 layers; Default netclass 0.127/0.127 with 0.45/0.2 vias, Power 0.4 with 0.6/0.3 vias (already in `gen_pcb.py`, do not touch).
- GP0–GP22 and GP26 keep their functions. GP24 = `MIDI_TX`, GP25 = `MIDI_RX`, GP27 = `VBUS_SENSE`, `FREE = (28,)`.
- MIDI TRS type A: Tip = DIN 5, Ring = DIN 4, Sleeve = DIN 2. 3.3 V output resistors 33 Ω (Ring from 3V3) and 10 Ω (Tip from buffer). Input: 220 Ω series, 1N4148 anti-parallel, H11L1, 4.7 kΩ pull-up to 3V3, sleeve of MIDI IN unconnected.
- Never guess an LCSC code: unknown → leave `LCSC` absent; `gen_fab.py` lists the blanks.
- Pinouts of U9 (74LVC1G17) and U10 (H11L1) are entered from their datasheets. Until a human confirms them against the datasheet, both symbols stay in `netlist.PINOUT_SIN_VERIFICAR` with "SIN VERIFICAR" in their `desc`.
- Commit messages in Spanish, no accents, ending with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Spec correction carried by this plan: the D-pad and diamond use an **8.5 mm** pitch between tact bodies (today's 12.5 mm does not fit beside a centred panel on 100 mm). Task 4 updates the spec sentence.

## Review Focus

Inputs the spec implies but no gate exercises, most likely to bite first:

1. A MIDI cable plugged into MIDI IN with reversed polarity (type B gear): current must flow through D3, not the opto LED backwards. Test in Task 2: D3's anode is on the Tip node (opto cathode) and its cathode on the Ring-side node (opto anode), anti-parallel to the LED. (Corrected by the final review: the plan first had Tip and Ring swapped.)
2. MIDI OUT loop current (5 mA at 3.3 V) must come from the buffer, never from the GPIO: Task 2 tests that `MIDI_TX` connects only to U9's input pin and to U1.
3. The MIDI IN sleeve must not be grounded (ground loop with the sender): Task 2 tests J6 pad `S` has no net while J7 pad `S` is GND.
4. `check_pinmap` reads `#define PIN_* <n>` and flags any PIN_ the PCB does not know: Task 1 tests that `config.h` and `pinmap.GPIO` agree in both directions, including the three new/moved names.
5. The packer's `FREE_REGIONS` are not checked against the outline by `gen_pcb.py`: the existing test `test_las_regiones_libres_caen_dentro_de_la_placa` covers 100 × 60 once `BOARD_H` changes; Task 5 also adds a test that no region overlaps the core box `NUCLEO ± (21, 16.5, 15, 11.5)`.

---

### Task 1: Board height, pin map and firmware header

**Files:**
- Modify: `params.py` (the `"BOARD_H"` entry, ~line 118)
- Modify: `pinmap.py` (`GPIO` dict ~line 45, `FREE` ~line 78, the "Libres" comment)
- Modify: `src/boards/pikocore_gamepad/config.h`
- Test: `tests/test_pinmap.py`

**Interfaces:**
- Produces: `pinmap.GPIO[24] == "MIDI_TX"`, `pinmap.GPIO[25] == "MIDI_RX"`, `pinmap.GPIO[27] == "VBUS_SENSE"`, `pinmap.FREE == (28,)`, `pinmap.UART1_TX_OK`, `pinmap.UART1_RX_OK`, `params.v("BOARD_H") == 60.0`. Later tasks read these.

- [ ] **Step 1: Write the failing tests**

In `tests/test_pinmap.py`, replace the three tests that pin today's values and add the UART1 pairing test:

```python
    def test_los_gpio_que_eran_internos_del_modulo_hacen_lo_mismo(self):
        # GP23 y GP29 hacian, DENTRO del modulo, modo del regulador y VSYS/3.
        # GP24 lo hacia VBUS_SENSE; con MIDI pasa a GP27 (ver abajo).
        self.assertEqual(pinmap.GPIO[23], "BB_PS")
        self.assertEqual(pinmap.GPIO[27], "VBUS_SENSE")
        self.assertEqual(pinmap.GPIO[29], "VSYS_ADC")

    def test_midi_usa_el_par_tx_rx_de_uart1(self):
        # MIDI va por UART de hardware, no por PIO. UART1 tiene TX en
        # GP4/8/20/24 y RX en GP5/9/21/25 (RP2350 datasheet, tabla de
        # funciones GPIO): TX y RX tienen que ser un par del MISMO bloque.
        tx = pinmap.gpio_of("MIDI_TX")
        rx = pinmap.gpio_of("MIDI_RX")
        self.assertIn(tx, pinmap.UART1_TX_OK)
        self.assertIn(rx, pinmap.UART1_RX_OK)
        self.assertEqual(rx, tx + 1)

    def test_queda_exactamente_un_pin_libre(self):
        # GP28 (con ADC). GP25 paso a MIDI_RX y GP27 a VBUS_SENSE.
        self.assertEqual(sorted(pinmap.FREE), [28])
```

Delete `test_quedan_exactamente_tres_pines_libres` (replaced above). In the ADC test (~line 67, "GP26-29 tienen ADC") change the loop so it only asserts GP28 is free:

```python
        for g in (28,):
            self.assertIn(g, pinmap.FREE)
```

Add to `tests/test_params.py`:

```python
    def test_la_placa_mide_100_por_60(self):
        # Disposicion estilo Game Boy Micro (spec 2026-10-15): el alto baja
        # de 80 a 60; el ancho no cambia.
        self.assertEqual(params.v("BOARD_W"), 100.0)
        self.assertEqual(params.v("BOARD_H"), 60.0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `"$KIPY" tests/run_tests.py 2>&1 | grep -a "FAIL\|ERROR\|^Ran"`
Expected: FAIL on `test_midi_usa_el_par_tx_rx_de_uart1` (AttributeError `UART1_TX_OK`), `test_queda_exactamente_un_pin_libre`, `test_los_gpio_que_eran_internos...` (GP27 missing) and `test_la_placa_mide_100_por_60`.

- [ ] **Step 3: Change `pinmap.py`**

After `UART0_RX_OK` add:

```python
UART1_TX_OK = (4, 8, 20, 24)
UART1_RX_OK = (5, 9, 21, 25)
```

In `GPIO` replace the GP24 line and add GP25/GP27:

```python
    24: "MIDI_TX",      # UART1 TX -> buffer 74LVC1G17 -> MIDI OUT (TRS tipo A)
    25: "MIDI_RX",      # UART1 RX <- opto H11L1 <- MIDI IN
    26: "LCD_TE",      # tearing effect del panel (entrada, opcional)
    27: "VBUS_SENSE",  # 1 = USB conectado (100k/200k desde VBUS); era GP24
```

Replace the "Libres" comment and `FREE`:

```python
# Libre: GP28 (con ADC). GP25 (el LED del modulo) y GP24 son el UART1 del
# MIDI; VBUS_SENSE, que estaba en GP24, paso a GP27 para liberar ese par.
FREE = (28,)
```

Update the module docstring sentence "GP23/24/29 hacen lo mismo ... y GP25 ... queda libre" to: "GP23/29 hacen lo mismo que hacian DENTRO del modulo; GP24/25 son el UART1 del MIDI (spec 2026-10-15) y VBUS_SENSE vive en GP27."

- [ ] **Step 4: Change `params.py`**

```python
    "BOARD_H": Param(
        60.00, True,
        "Alto de la disposicion estilo Game Boy Micro (spec 2026-10-15): "
        "decision de diseno, no medicion. Era 80 (DXF de Rhino).",
        "V-0"),
```

- [ ] **Step 5: Change `config.h`**

Replace the `PIN_VBUS_SENSE` line and add the two MIDI pins, keeping the numeric order:

```c
#define PIN_MIDI_TX      24  // UART1 TX -> 74LVC1G17 -> MIDI OUT, TRS type A, 31250 baud
#define PIN_MIDI_RX      25  // UART1 RX <- H11L1 opto <- MIDI IN
#define PIN_LCD_TE       26  // panel tearing-effect out (input, optional, unused)
#define PIN_VBUS_SENSE   27  // in: 1 = USB present (100k/200k from VBUS)
```

Update the header comment line 5 to "(branch hw/chipdown-rp2350, which adds BB_PS/VSYS_ADC, MIDI_TX/MIDI_RX on UART1, and moves VBUS_SENSE to GP27)".

- [ ] **Step 6: Run tests and gate G-4**

Run: `"$KIPY" tests/run_tests.py 2>&1 | grep -a "^Ran\|^OK\|FAIL"` → `OK`.
Run: `"$KIPY" checks/check_pinmap.py` → exit 0, no discrepancies.

- [ ] **Step 7: Commit**

```bash
git add params.py pinmap.py tests/test_pinmap.py tests/test_params.py ../../../src/boards/pikocore_gamepad/config.h
git commit -m "hw: placa de 100x60 y UART1 en GP24/25 para MIDI (VBUS_SENSE a GP27)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: MIDI parts in the netlist

**Files:**
- Modify: `netlist.py` (`SYMS` ~line 64–360, `PINOUT_SIN_VERIFICAR` ~line 359, a new `INSTANCES +=` block after the jack block ~line 760, `LCSC_PASIVOS` ~line 955)
- Test: `tests/test_netlist.py`

**Interfaces:**
- Consumes: `pinmap.GPIO` (U1 pads 36/37/41 get `MIDI_TX`/`MIDI_RX`/`VBUS_SENSE` through `_mcu_nets()` automatically).
- Produces: refs `J6`, `J7`, `U9`, `U10`, `D3`, `R40`, `R41`, `R42`, `R43`, `C56`; nets `MIDI_TX`, `MIDI_TX_BUF`, `MIDI_OUT_T`, `MIDI_OUT_R`, `MIDI_IN_T`, `MIDI_IN_A`, `MIDI_IN_K`, `MIDI_RX`; symbols `H11L1`, `LVC1G17`, `D_1N4148`. Task 3 lists the refs on a sheet; Task 5 places them.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_netlist.py` (helpers `nets_of(ref)` and `pin_names(sym)` already exist at the top):

```python
class TestMidi(unittest.TestCase):
    """MIDI IN/OUT en TRS tipo A (spec 2026-10-15)."""

    def test_los_jacks_midi_reusan_el_simbolo_y_la_huella_del_de_auriculares(self):
        for ref in ("J6", "J7"):
            inst = [i for i in netlist.INSTANCES if i[1] == ref][0]
            self.assertEqual(inst[0], "JACK_AUDIO")
            self.assertEqual(inst[6]["FP"], netlist.JACK_FP)

    def test_midi_out_tiene_la_malla_a_masa_y_midi_in_no(self):
        # La norma pide que el RECEPTOR no aterrice la malla (lazo de masa
        # con el emisor). El emisor si.
        self.assertEqual(nets_of("J7")["S"], "GND")
        self.assertEqual(nets_of("J6")["S"], netlist.NC)

    def test_midi_out_es_tipo_a_de_3v3(self):
        # Tipo A: Tip = DIN 5 (sumidero, desde el driver), Ring = DIN 4
        # (fuente, desde 3V3). Norma 3.3V (CA-033): 10R al driver, 33R a Vdd.
        self.assertEqual(nets_of("J7")["T"], "MIDI_OUT_T")
        self.assertEqual(nets_of("J7")["R"], "MIDI_OUT_R")
        r41 = [i for i in netlist.INSTANCES if i[1] == "R41"][0]
        r40 = [i for i in netlist.INSTANCES if i[1] == "R40"][0]
        self.assertEqual(r41[2], "10R")
        self.assertEqual(set(r41[5].values()), {"MIDI_OUT_T", "MIDI_TX_BUF"})
        self.assertEqual(r40[2], "33R")
        self.assertEqual(set(r40[5].values()), {"MIDI_OUT_R", "3V3"})

    def test_el_gpio_de_midi_tx_solo_ve_al_buffer(self):
        # La corriente del lazo (5mA) la pone U9, nunca el GPIO.
        usan = [i[1] for i in netlist.INSTANCES if "MIDI_TX" in i[5].values()]
        self.assertEqual(sorted(usan), ["U1", "U9"])

    def test_midi_in_tiene_opto_con_diodo_antiparalelo(self):
        # Tip -> 220R -> anodo del LED (MIDI_IN_A); Ring -> catodo (MIDI_IN_K).
        # D3 va en antiparalelo: anodo en MIDI_IN_K, catodo en MIDI_IN_A.
        self.assertEqual(nets_of("J6")["T"], "MIDI_IN_T")
        self.assertEqual(nets_of("J6")["R"], "MIDI_IN_K")
        self.assertEqual(set(nets_of("R42").values()), {"MIDI_IN_T", "MIDI_IN_A"})
        d3 = nets_of("D3")
        self.assertEqual(d3["1"], "MIDI_IN_A")   # pin 1 = catodo (huella KiCad)
        self.assertEqual(d3["2"], "MIDI_IN_K")   # pin 2 = anodo
        u10 = nets_of("U10")
        self.assertEqual(u10["1"], "MIDI_IN_A")  # anodo del LED
        self.assertEqual(u10["2"], "MIDI_IN_K")  # catodo del LED
        self.assertEqual(u10["4"], "MIDI_RX")    # salida Schmitt (colector abierto)
        self.assertEqual(u10["5"], "GND")
        self.assertEqual(u10["6"], "3V3")
        self.assertEqual(set(nets_of("R43").values()), {"MIDI_RX", "3V3"})

    def test_el_buffer_de_salida_sigue_el_sc70_de_ti(self):
        # SN74LVC1G17 DCK: 1 NC, 2 A, 3 GND, 4 Y, 5 VCC.
        u9 = nets_of("U9")
        self.assertEqual(u9["2"], "MIDI_TX")
        self.assertEqual(u9["3"], "GND")
        self.assertEqual(u9["4"], "MIDI_TX_BUF")
        self.assertEqual(u9["5"], "3V3")

    def test_los_pinouts_nuevos_estan_marcados_sin_verificar(self):
        for s in ("H11L1", "LVC1G17"):
            self.assertIn(s, netlist.PINOUT_SIN_VERIFICAR)

    def test_el_diodo_de_senal_tiene_el_catodo_en_el_pin_1(self):
        # Como D_Schottky y como la huella D_SOD-123 de KiCad (pad 1 = K).
        self.assertEqual([p[1] for p in netlist.SYMS["D_1N4148"]["pins"]], ["K", "A"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `"$KIPY" tests/run_tests.py 2>&1 | grep -a "FAIL\|ERROR\|^Ran" | head`
Expected: the 8 new tests fail (IndexError on missing refs, KeyError on missing symbols).

- [ ] **Step 3: Add the three symbols to `SYMS`**

Right after the `"D_Schottky"` entry:

```python
    "D_1N4148": dict(
        ref="D", w=2.54, h=7.62,
        desc="Diodo de senal 1N4148W (SOD-123). Pin 1 = CATODO, como todos los "
             "footprints de diodo de KiCad; pin 2 = anodo. Antiparalelo al LED "
             "del opto de MIDI IN: protege contra un cable con polaridad al reves.",
        ds="",
        pins=[("1", "K", 5.08, 0.0, 180), ("2", "A", -5.08, 0.0, 0)],
    ),
    "H11L1": dict(
        ref="U", w=10.16, h=10.16,
        desc="Optoacoplador con salida Schmitt (onsemi H11L1M, SMDIP-6). Vcc "
             "minimo 3V: funciona a 3V3. PINOUT SIN VERIFICAR contra el "
             "datasheet (tomado de memoria): 1 anodo, 2 catodo, 3 NC, "
             "4 salida (colector abierto), 5 GND, 6 Vcc.",
        ds="",
        pins=[("1", "A", -10.16, 2.54, 0), ("2", "K", -10.16, 0.0, 0),
              ("3", "NC", -10.16, -2.54, 0), ("4", "VO", 10.16, 0.0, 180),
              ("5", "GND", 10.16, -2.54, 180), ("6", "VCC", 10.16, 2.54, 180)],
    ),
    "LVC1G17": dict(
        ref="U", w=7.62, h=7.62,
        desc="Buffer Schmitt de una compuerta SN74LVC1G17 (SC-70-5 / DCK). "
             "Toma los 5mA del lazo MIDI en vez del GPIO. PINOUT SIN VERIFICAR "
             "contra el datasheet (tomado de memoria): 1 NC, 2 A, 3 GND, "
             "4 Y, 5 VCC.",
        ds="",
        pins=[("1", "NC", -7.62, 2.54, 0), ("2", "A", -7.62, 0.0, 0),
              ("3", "GND", -7.62, -2.54, 0), ("4", "Y", 7.62, 0.0, 180),
              ("5", "VCC", 7.62, 2.54, 180)],
    ),
```

Change `PINOUT_SIN_VERIFICAR = ()` to `PINOUT_SIN_VERIFICAR = ("H11L1", "LVC1G17")`.

- [ ] **Step 4: Add the instances**

After the speaker block (the `INSTANCES += [...]` that contains `J5`), add:

```python
# ==================================================================== MIDI
#
#   MIDI OUT (J7, TRS tipo A): Tip = DIN 5, Ring = DIN 4, Sleeve = DIN 2.
#       3V3 -[33R R40]- Ring        MIDI_TX -> U9 (74LVC1G17) -[10R R41]- Tip
#   Norma MIDI 1.0 electrica, variante 3.3V (CA-033). U9 pone los 5mA del
#   lazo; el GPIO solo ve la entrada CMOS del buffer.
#
#   MIDI IN (J6): Tip -[220R R42]- anodo del LED de U10 (H11L1); Ring - catodo.
#   D3 antiparalelo al LED. La salida Schmitt de U10 es colector abierto:
#   R43 4k7 a 3V3 -> MIDI_RX. La MALLA de J6 queda al aire: el receptor no
#   aterriza el blindaje (lazo de masa con el emisor).
INSTANCES += [
    ("JACK_AUDIO", "J7", "MIDI OUT", 280.0, 300.0, {
        "S": "GND", "T": "MIDI_OUT_T", "R": "MIDI_OUT_R", "TN": NC, "RN": NC},
     {"FP": JACK_FP}),
    ("R", "R40", "33R", 288.0, 290.0,
     {"1": "3V3", "2": "MIDI_OUT_R"}, {"FP": R_FP}),
    ("R", "R41", "10R", 288.0, 300.0,
     {"1": "MIDI_TX_BUF", "2": "MIDI_OUT_T"}, {"FP": R_FP}),
    ("LVC1G17", "U9", "74LVC1G17", 300.0, 300.0,
     {"1": NC, "2": "MIDI_TX", "3": "GND", "4": "MIDI_TX_BUF", "5": "3V3"},
     {"FP": "Package_TO_SOT_SMD:SOT-353_SC-70-5"}),
    ("JACK_AUDIO", "J6", "MIDI IN", 280.0, 330.0, {
        "S": NC, "T": "MIDI_IN_T", "R": "MIDI_IN_K", "TN": NC, "RN": NC},
     {"FP": JACK_FP}),
    ("R", "R42", "220R", 288.0, 325.0,
     {"1": "MIDI_IN_T", "2": "MIDI_IN_A"}, {"FP": R_FP}),
    ("D_1N4148", "D3", "1N4148W", 288.0, 335.0,
     {"1": "MIDI_IN_A", "2": "MIDI_IN_K"}, {"FP": D_FP}),
    ("H11L1", "U10", "H11L1M", 300.0, 330.0,
     {"1": "MIDI_IN_A", "2": "MIDI_IN_K", "3": NC, "4": "MIDI_RX",
      "5": "GND", "6": "3V3"},
     {"FP": "Package_DIP:SMDIP-6_W7.62mm"}),
    ("R", "R43", "4.7k", 312.0, 325.0,
     {"1": "3V3", "2": "MIDI_RX"}, {"FP": R_FP}),
    ("C", "C56", "100nF", 312.0, 335.0,
     {"1": "3V3", "2": "GND"}, {"FP": C_FP}),
]
```

`D_FP` is `"Diode_SMD:D_SOD-123"` (defined ~line 564, before this block). `10R`, `33R` and `220R` have no entry in `LCSC_PASIVOS`: do not add codes; `gen_fab.py` will list them as blanks.

- [ ] **Step 5: Run the tests**

Run: `"$KIPY" tests/run_tests.py 2>&1 | grep -a "^Ran\|^OK\|FAIL"` → `OK`. The existing tests `test_todos_los_footprints_referenciados_existen` and `test_no_hay_referencias_duplicadas` (G-5) cover the new footprints and refs.

- [ ] **Step 6: Commit**

```bash
git add netlist.py tests/test_netlist.py
git commit -m "hw: MIDI IN/OUT en TRS tipo A (H11L1, 74LVC1G17) en el netlist" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: Schematic sheet for MIDI

**Files:**
- Modify: `gen_sch.py` (`HOJAS` ~line 80–137, `NOTAS` ~line 269, `NOTA_RAIZ` text)
- Test: `tests/test_netlist.py` (sheet coverage) — `gen_sch.py` itself raises `SystemExit("REPARTO DE HOJAS MAL")` if a ref is unassigned, which is the gate here.

**Interfaces:**
- Consumes: the ten MIDI refs from Task 2.
- Produces: `07_midi.kicad_sch` and an updated root sheet; `pikocore_gamepad.net` regenerated by `kicad-cli`.

- [ ] **Step 1: Add the sheet**

Append to `HOJAS` after the `05_salidas` entry:

```python
    ("07_midi", "MIDI - entrada y salida TRS tipo A", [
        "J7", "U9", "R40", "R41",                  # MIDI OUT
        "J6", "R42", "D3", "U10", "R43", "C56",    # MIDI IN
    ], ["NOTA_MIDI"]),
```

- [ ] **Step 2: Add the note**

In `NOTAS`, after `"NOTA_SPK"`:

```python
    "NOTA_MIDI":
        "MIDI por UART1 (GP24 TX, GP25 RX) en jacks 3.5mm TRS TIPO A, el estandar de la MIDI\n"
        "Association (RP-054): Tip = DIN 5, Ring = DIN 4, Sleeve = DIN 2. Korg usa tipo B:\n"
        "hace falta un adaptador para esos equipos.\n"
        "\n"
        "SALIDA (J7): norma electrica 3.3V (CA-033): 33R de 3V3 al Ring, 10R del buffer al Tip.\n"
        "U9 (74LVC1G17) pone los 5mA del lazo; el GPIO ve solo una entrada CMOS.\n"
        "\n"
        "ENTRADA (J6): 220R + H11L1 (salida Schmitt, colector abierto, pull-up 4k7). D3 en\n"
        "antiparalelo al LED aguanta un cable al reves. La MALLA de J6 NO va a masa: la norma\n"
        "pide que el receptor no aterrice el blindaje.\n"
        "\n"
        "PINOUTS DE U9 Y U10 SIN VERIFICAR contra sus datasheets (ver netlist.PINOUT_SIN_VERIFICAR).",
```

In `NOTA_RAIZ` change `100x80mm` to `100x60mm, disposicion estilo Game Boy Micro` and `las cinco hojas` to `las seis hojas`. Add after the USB sentence: `MIDI IN/OUT en TRS tipo A (hoja 7).`

- [ ] **Step 3: Regenerate the schematic and netlist, run ERC**

```bash
"$KIPY" gen_sch.py
"$KICLI" sch export netlist -o pikocore_gamepad.net pikocore_gamepad.kicad_sch
"$KICLI" sch erc --severity-all --exit-code-violations -o logs/erc.rpt pikocore_gamepad.kicad_sch; echo "exit $?"
tail -n 2 logs/erc.rpt
```

Expected: `gen_sch.py` prints `OK -> ...07_midi.kicad_sch`; ERC exit 0, `Errores0, Avisos 0`. If ERC reports the NC sleeve of J6 or U9 pin 1 as unconnected, the generator already emits no-connect flags for `NC` pins (the jack's `TN` pins use it today); check `07_midi.kicad_sch` contains `(no_connect` at those pins before changing anything.

- [ ] **Step 4: Run the tests and commit**

Run: `"$KIPY" tests/run_tests.py 2>&1 | grep -a "^Ran\|^OK\|FAIL"` → `OK`.

```bash
git add gen_sch.py 07_midi.kicad_sch pikocore_gamepad.kicad_sch pikocore_gamepad.kicad_sym pikocore_gamepad.net 0*.kicad_sch
git commit -m "hw: hoja 07_midi en el esquematico" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: Front placement (Micro layout)

**Files:**
- Modify: `placements.py` (front block, lines ~26–107; keep the back block for Task 5)
- Modify: `docs/superpowers/specs/2026-10-15-pikocore-gamepad-micro-layout-midi-design.md` (pitch sentence)
- Test: `tests/test_netlist.py` (class with `test_los_gatillos_L_y_R_quedan_simetricos`)

**Interfaces:**
- Consumes: `params.v("BOARD_W") == 100`, `params.v("BOARD_H") == 60`.
- Produces: the front rows of `PLACEMENTS` with the coordinates below; `_LCD_X = 50.0`, `_LCD_Y = 24.0`.

Origins are the footprint origins (`SW_PUSH_6mm`: pad 1, body centre at origin + (3.25, 2.25); `PTS645` angled: pad 1, body centre at origin + 2.25 in X; `LCD_LH133T_24P`: centre of the active area).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_netlist.py`, in the same class as the trigger symmetry test:

```python
    def test_el_frente_es_la_disposicion_micro(self):
        # Spec 2026-10-15: panel al centro, cruceta a la izquierda y rombo a
        # la derecha, todos centrados en y=24 (area activa del panel). Las
        # cruces miden 8.5mm de paso; cuerpos = origen + (3.25, 2.25).
        import placements
        pos = {ref: (x, y) for ref, _, x, y, _, _ in placements.PLACEMENTS}
        self.assertEqual(pos["LCD1"], (50.0, 24.0))
        cuerpo = lambda r: (pos[r][0] + 3.25, pos[r][1] + 2.25)
        self.assertEqual(cuerpo("SW1"), (18.0, 15.5))   # UP
        self.assertEqual(cuerpo("SW3"), (9.5, 24.0))    # LEFT
        self.assertEqual(cuerpo("SW4"), (26.5, 24.0))   # RIGHT
        self.assertEqual(cuerpo("SW2"), (18.0, 32.5))   # DOWN
        self.assertEqual(cuerpo("SW5"), (82.0, 15.5))   # X
        self.assertEqual(cuerpo("SW6"), (73.5, 24.0))   # Y
        self.assertEqual(cuerpo("SW7"), (90.5, 24.0))   # A
        self.assertEqual(cuerpo("SW8"), (82.0, 32.5))   # B
        self.assertEqual(cuerpo("SW12"), (76.0, 46.0))  # SELECT
        self.assertEqual(cuerpo("SW11"), (88.0, 46.0))  # START
        self.assertEqual(pos["J4"], (50.0, 52.4))

    def test_todo_el_frente_cae_dentro_de_100x60(self):
        import placements
        for ref, _, x, y, _, flip in placements.PLACEMENTS:
            if flip:
                continue
            self.assertTrue(0 <= x <= 100 and 0 <= y <= 60,
                            f"{ref} en ({x}, {y}) fuera de la placa")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"$KIPY" tests/run_tests.py 2>&1 | grep -a "FAIL\|^Ran" | head -3` → both new tests FAIL.

- [ ] **Step 3: Rewrite the front block of `placements.py`**

Replace from `_PANEL_TOP = 3.0` through the `SW15` row with:

```python
# Disposicion estilo Game Boy Micro (spec 2026-10-15): el panel al CENTRO,
# la cruceta a la izquierda y el rombo a la derecha, todos centrados en
# y=24. El origen del panel es el centro del area activa.
_LCD_X = BOARD_W / 2
_LCD_Y = 24.0

PLACEMENTS = [
    # ================================================ FRENTE: display
    ("LCD1", "gamesetup_fp:LCD_LH133T_24P",             _LCD_X, _LCD_Y, 0, False),
    # Conector del FPC debajo del panel, en el frente. El vidrio termina en
    # y = 24 - 11.7 - 1.56 + 29.22 = 39.96 y el flex llega desplegado
    # 14.93 mas abajo; con rot 180 los contactos del conector caen 1.62 por
    # debajo de su origen, asi que el origen va 12.4 bajo el vidrio, igual
    # que en la placa de 80 (44.60 = 32.22 + 12.4). Cuerpo x 41.7..58.3.
    ("J4",  "gamesetup_lcsc:FPC-SMD_24P-P0.50_FPC-05FB-24PH20",
      _LCD_X,   52.40, 180, False),

    # ================================================ FRENTE: controles
    # Cruceta: cuatro tacts 6x6 con paso 8.5mm (era 12.5: no entra al lado
    # de un panel centrado en 100mm). El origen del SW_PUSH_6mm es el pad 1
    # y el cuerpo queda en (x+3.25, y+2.25). Centro de la cruz (18, 24).
    ("SW1", "Button_Switch_THT:SW_PUSH_6mm",   14.75,   13.25, 0, False),  # UP    cuerpo (18.0, 15.5)
    ("SW3", "Button_Switch_THT:SW_PUSH_6mm",    6.25,   21.75, 0, False),  # LEFT  cuerpo ( 9.5, 24.0)
    ("SW4", "Button_Switch_THT:SW_PUSH_6mm",   23.25,   21.75, 0, False),  # RIGHT cuerpo (26.5, 24.0)
    ("SW2", "Button_Switch_THT:SW_PUSH_6mm",   14.75,   30.25, 0, False),  # DOWN  cuerpo (18.0, 32.5)
    # Rombo X/Y/A/B, espejo de la cruceta: centro (82, 24).
    ("SW5", "Button_Switch_THT:SW_PUSH_6mm",   78.75,   13.25, 0, False),  # X     cuerpo (82.0, 15.5)
    ("SW6", "Button_Switch_THT:SW_PUSH_6mm",   70.25,   21.75, 0, False),  # Y     cuerpo (73.5, 24.0)
    ("SW7", "Button_Switch_THT:SW_PUSH_6mm",   87.25,   21.75, 0, False),  # A     cuerpo (90.5, 24.0)
    ("SW8", "Button_Switch_THT:SW_PUSH_6mm",   78.75,   30.25, 0, False),  # B     cuerpo (82.0, 32.5)
    # L / R: tact angulado en el borde SUPERIOR, en las esquinas. El cuerpo
    # esta 2.25 hacia +X del origen; 9.75 y 85.75 dejan los cuerpos en 12 y
    # 88, simetricos respecto de x=50 (el test lo verifica). y=1.89 como
    # siempre: pads a 1mm del borde, actuador asomando ~2mm.
    ("SW9",  "Button_Switch_THT:SW_Tactile_SPST_Angled_PTS645Vx39-2LFS",
       9.75,    1.89, 0,  False),  # L
    ("SW10", "Button_Switch_THT:SW_Tactile_SPST_Angled_PTS645Vx39-2LFS",
      85.75,    1.89, 0, False),  # R
    # SELECT y START bajo el rombo, como en la Micro: cuerpos en (76, 46) y
    # (88, 46), 7.5mm por debajo de B.
    ("SW12", "Button_Switch_THT:SW_PUSH_6mm",   72.75,   43.75, 0, False),  # SELECT
    ("SW11", "Button_Switch_THT:SW_PUSH_6mm",   84.75,   43.75, 0, False),  # START
    # Slide de encendido en el borde inferior, a la izquierda del conector
    # del flex (J4 termina en x=41.7; el slide ocupa 19.85..30.15). y=57.70:
    # los pads de anclaje quedan a 1mm del borde y el actuador asoma 3.16mm,
    # como en la placa de 80 (77.70).
    ("SW15", "gamesetup_lcsc:SW-TH_SK12D07VG3",             25.00,    57.70, 0, False),
```

Leave the back block (from `# ===== DORSO` on) as it is for now; Task 5 rewrites it. Replace the whole `FREE_REGIONS` list with `FREE_REGIONS = []` (its regions reach y 76 and would fail `test_las_regiones_libres_caen_dentro_de_la_placa` on a 60 mm board; Task 5 writes the real list).

- [ ] **Step 4: Fix the spec sentence**

In the spec's "Front layout" paragraph replace `Each button group keeps today's internal pitch (6 mm tacts, 8.5 mm between centres in a cross).` with `Each button group uses 6 mm tacts at 8.5 mm between body centres in a cross (today's 12.5 mm pitch does not fit beside a centred panel on 100 mm).`

- [ ] **Step 5: Run the tests**

Run: `"$KIPY" tests/run_tests.py 2>&1 | grep -a "^Ran\|^OK\|FAIL"` → `OK` (the trigger symmetry test passes with bodies at 12 and 88).

- [ ] **Step 6: Commit**

```bash
git add placements.py tests/test_netlist.py ../../../docs/superpowers/specs/2026-10-15-pikocore-gamepad-micro-layout-midi-design.md
git commit -m "hw: frente estilo Game Boy Micro en 100x60" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: Back placement, core position and packer regions

**Files:**
- Modify: `placements.py` (back block and `FREE_REGIONS`, `NUCLEO`)
- Test: `tests/test_netlist.py`
- Run: `gen_pcb.py`, `checks/check_placement.py`

**Interfaces:**
- Consumes: front rows from Task 4; MIDI refs from Task 2.
- Produces: `NUCLEO = (53.0, 37.5, 90.0)`; every back-side anchored part inside 100 × 60; `FREE_REGIONS` for the packer; a board that passes `check_placement.py` and pre-route DRC with 0 errors.

The numbers below are the starting point. They were checked on paper against the front THT pads with 1 mm pad radius (D-pad pads end at x 29.75 / y 35.75; diamond pads start at x 69.25; B's pads end at y 35.75; Select/Start pads span y 42.75–49.25; slide at x 19.85–30.15, y 53.8+), not against a render. `check_placement.py` and DRC decide; expect two or three adjustments.

- [ ] **Step 1: Write the failing tests**

```python
    def test_el_nucleo_queda_detras_del_panel(self):
        # El bloque del RP2350A (rp_core.py) ocupa NUCLEO + (-21..+15, -16.5..
        # +11.5) a rot 90. Detras del panel no hay patas pasantes del frente.
        import placements
        x, y, rot = placements.NUCLEO
        self.assertEqual(rot, 90.0)
        self.assertGreaterEqual(x - 21, 30.0)
        self.assertLessEqual(x + 15, 70.0)
        self.assertGreaterEqual(y - 16.5, 19.0)
        self.assertLessEqual(y + 11.5, 50.0)

    def test_las_regiones_libres_no_pisan_el_nucleo(self):
        import placements
        x, y, _ = placements.NUCLEO
        core = (x - 21, y - 16.5, x + 15, y + 11.5)
        for r in placements.FREE_REGIONS:
            solapa = not (r[2] <= core[0] or r[0] >= core[2]
                          or r[3] <= core[1] or r[1] >= core[3])
            self.assertFalse(solapa, f"region {r} pisa el nucleo {core}")

    def test_los_jacks_salen_por_el_borde_superior(self):
        import placements
        pos = {ref: (x, y, rot, flip) for ref, _, x, y, rot, flip in placements.PLACEMENTS}
        for ref in ("J1", "J6", "J7"):
            x, y, rot, flip = pos[ref]
            self.assertTrue(flip, f"{ref} tiene que ir en el dorso")
            self.assertEqual(rot, 180, f"{ref}: barril hacia -Y")
            self.assertEqual(y, 3.0, f"{ref}: pads a 3mm del borde")
            self.assertTrue(25 <= x <= 75, f"{ref} fuera de la franja de jacks")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `"$KIPY" tests/run_tests.py 2>&1 | grep -a "FAIL\|^Ran" | head` → the three new tests FAIL.

- [ ] **Step 3: Rewrite the back block of `placements.py`**

Replace everything from `# ===== DORSO: USB, carga, 3V3` to the end of `PLACEMENTS`, and `FREE_REGIONS` and `NUCLEO`, with:

```python
    # ================================================ DORSO: jacks (arriba)
    # Los tres jacks salen por el borde SUPERIOR, entre los gatillos (cuerpos
    # x 8..18 y 84..94): los cables apuntan lejos de las manos. Con flip y
    # rot 180 el barril cruza el borde de arriba; y=3.0 deja los pads a 3mm
    # del canto (espejo del 77.0 de la placa de 80). El cuerpo entra 14.5mm
    # en la placa. Orden: MIDI IN, auriculares, MIDI OUT; el opto queda a la
    # izquierda de J6 y el buffer a la derecha de J7, cada uno con su jack.
    ("J6",  "Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal",
      36.00,    3.00, 180, True),   # MIDI IN   cuerpo x 31.4..40.6
    ("J1",  "Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal",
      50.00,    3.00, 180, True),   # phones    cuerpo x 45.4..54.6
    ("J7",  "Connector_Audio:Jack_3.5mm_CUI_SJ1-3535NG_Horizontal",
      64.00,    3.00, 180, True),   # MIDI OUT  cuerpo x 59.4..68.6
    # Opto a rot 90 (patas gull-wing a lo ancho, 10.2mm): x 17.9..28.1,
    # y 4.2..13.8, a la derecha de las patas del gatillo L (hasta x 17.8).
    ("U10", "Package_DIP:SMDIP-6_W7.62mm",                 23.00,    9.00, 90, True),
    ("R42", "Resistor_SMD:R_0603_1608Metric",              30.50,    4.00, 90, True),
    ("D3",  "Diode_SMD:D_SOD-123",                         30.50,    9.00, 90, True),
    ("R43", "Resistor_SMD:R_0603_1608Metric",              30.50,   14.00, 90, True),
    ("C56", "Capacitor_SMD:C_0603_1608Metric",             30.50,   18.00, 90, True),
    ("U9",  "Package_TO_SOT_SMD:SOT-353_SC-70-5",          72.50,    6.00, 0, True),
    ("R40", "Resistor_SMD:R_0603_1608Metric",              72.50,    9.50, 0, True),
    ("R41", "Resistor_SMD:R_0603_1608Metric",              72.50,   12.50, 0, True),
    # Deteccion de auriculares, bajo el cuerpo de J1 (termina en y 14.5) y
    # sobre el nucleo (empieza en y 21).
    ("R15", "Resistor_SMD:R_0603_1608Metric",              44.00,   17.00, 0, True),
    ("R18", "Resistor_SMD:R_0603_1608Metric",              50.00,   17.00, 0, True),
    ("C29", "Capacitor_SMD:C_0603_1608Metric",             56.00,   17.00, 0, True),

    # ================================================ DORSO: USB, carga (abajo-izq)
    # USB-C en el borde INFERIOR con la boca hacia +Y. rot 180 con flip es la
    # hipotesis; check_placement.py avisa si la boca mira adentro, y entonces
    # va rot 0. y=55.4: boca a 0.4mm del canto (la boca esta a 4.22 del
    # origen). Cuerpo x 6.65..17.35; el slide empieza en 19.85.
    ("J2",  "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A",
      12.00,   55.40, 180, True),
    ("R29", "Resistor_SMD:R_0603_1608Metric",               5.00,   51.00, 0, True),
    ("R30", "Resistor_SMD:R_0603_1608Metric",              22.00,   51.00, 0, True),
    # Cargador ETA6096 y su lazo, encima del USB; misma geometria interna que
    # en la placa de 80 (SW al inductor por el camino corto), corrida
    # (+2, +11).
    ("D1",  "Diode_SMD:D_SOD-123F",                        13.00,   37.50, 0, True),
    ("U8",  "gamesetup_lcsc:DFN-10_L3.0-W3.0-P0.50-BL-EP2.4-1",
       8.00,   42.00, 0, True),
    ("C48", "Capacitor_SMD:C_0603_1608Metric",              4.00,   41.00, 90, True),
    ("C49", "Capacitor_SMD:C_0805_2012Metric",             12.20,   41.50, 90, True),
    ("R31", "Resistor_SMD:R_0603_1608Metric",               4.00,   44.40, 90, True),
    ("L4",  "Inductor_SMD:L_1210_3225Metric",               8.00,   46.60, 0, True),
    ("C50", "Capacitor_SMD:C_0603_1608Metric",             12.20,   46.60, 90, True),
    ("D2",  "Diode_SMD:D_SOD-123F",                        16.50,   46.60, 0, True),
    # Bateria: PicoBlade vertical en el margen izquierdo. Las patas de LEFT
    # (SW3) ocupan x 5.25..7.25 en y 20.75..27.25; a rot 90 el conector
    # queda en x 1.5..5.5, y 30.25..35.75.
    ("J3",  "Connector_Molex:Molex_PicoBlade_53398-0271_1x02-1MP_P1.25mm_Vertical",
       3.50,   33.00, 90, True),
    # BOOTSEL y RUN en el margen izquierdo, arriba de las patas de LEFT.
    ("SW13", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",  3.50,   10.00, 90, True),
    ("SW14", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",  3.50,   17.00, 90, True),
    # Sensado de VBUS y VSYS, entre el cargador y el slide (patas de DOWN
    # hasta y 35.75; slide desde y 53.8).
    ("R35", "Resistor_SMD:R_0603_1608Metric",              22.00,   40.00, 90, True),
    ("R36", "Resistor_SMD:R_0603_1608Metric",              25.00,   40.00, 90, True),
    ("R37", "Resistor_SMD:R_0603_1608Metric",              28.00,   40.00, 90, True),
    ("R38", "Resistor_SMD:R_0603_1608Metric",              22.00,   45.00, 90, True),
    ("C55", "Capacitor_SMD:C_0603_1608Metric",             25.00,   45.00, 90, True),

    # ================================================ DORSO: 3V3 (banda derecha)
    # TPS63001 en la banda sin patas pasantes entre el rombo (pads hasta
    # y 35.75) y Select/Start (pads desde y 42.75), x 69.5..100. U7 a 180 con
    # L1/L2 enfrentados a L5 (dx 4.2, como en la placa de 80: las pistas
    # manuales U7_BB_L1/L2 dependen de ESA geometria relativa).
    ("U7",  "Package_SON:Texas_DRC0010J_ThermalVias",      80.00,   39.50, 180, True),
    ("L5",  "Inductor_SMD:L_1210_3225Metric",              84.20,   39.50, 90, True),
    ("C52", "Capacitor_SMD:C_0603_1608Metric",             88.00,   37.50, 0, True),
    ("C53", "Capacitor_SMD:C_0603_1608Metric",             88.00,   41.50, 0, True),
    ("C51", "Capacitor_SMD:C_0603_1608Metric",             76.00,   41.50, 0, True),
    ("R32", "Resistor_SMD:R_0603_1608Metric",              76.00,   37.50, 0, True),
    ("C54", "Capacitor_SMD:C_0603_1608Metric",             72.00,   37.50, 0, True),
    ("R33", "Resistor_SMD:R_0603_1608Metric",              72.00,   41.50, 0, True),
    ("R34", "Resistor_SMD:R_0603_1608Metric",              92.00,   37.50, 0, True),
    # Parlante: header en la columna del borde derecho, a la derecha de A
    # (pads hasta x 94.75, y 27.25). rot 90: x 94.25..99.75, y 27.5..34.5.
    ("J5",  "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
      97.00,   31.00, 90, True),

    # ================================================ DORSO: audio (banda inferior)
    # DAC, op-amp y los 470uF en la banda inferior central, detras de J4 (que
    # es SMD del frente: no estorba) y debajo del nucleo (y 49). x 31..69.5
    # entre el slide (hasta x 30.15) y Select (patas desde x 71.75).
    ("U5",  "gamesetup_lcsc:TSSOP-20_L6.5-W4.4-P0.65-LS6.4-BL", 36.00, 54.00, 0, True),
    ("C23", "Capacitor_SMD:CP_Elec_6.3x5.4",               45.00,   54.00, 0, True),
    ("C24", "Capacitor_SMD:CP_Elec_6.3x5.4",               55.00,   54.00, 0, True),
    ("U3",  "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",              64.50, 53.00, 0, True),
    ("R19", "Resistor_SMD:R_0603_1608Metric",              45.00,   58.20, 0, True),
    ("R20", "Resistor_SMD:R_0603_1608Metric",              55.00,   58.20, 0, True),
    # Class-D bajo Select (patas hasta y 49.25), a la izquierda del boost.
    ("U4",  "gamesetup_lcsc:MSOP-8_L3.0-W3.0-P0.65-LS5.0-BL",   74.00, 54.00, 0, True),
    # ================================================ DORSO: boost 5V
    # El lazo del TPS61023 se mueve ENTERO (+29, +50) desde la placa de 80:
    # manual_tracks.py tiene pistas entre U2, L1, C4 y C7 que dependen de la
    # geometria relativa del cluster. Queda en x 77.4..99, y 51.7..57.6.
    ("U2",  "Package_TO_SOT_SMD:SOT-563",                  89.00,   56.00, 0, True),
    ("L2",  "Inductor_SMD:L_1210_3225Metric",              83.80,   56.00, 0, True),
    ("C4",  "Capacitor_SMD:C_0603_1608Metric",             78.20,   56.00, 0, True),
    ("L1",  "Inductor_SMD:L_1210_3225Metric",              93.40,   56.00, 180, True),
    ("C5",  "Capacitor_SMD:C_0805_2012Metric",             93.50,   52.50, 0, True),
    ("C7",  "Capacitor_SMD:C_0603_1608Metric",             97.20,   52.50, 0, True),
    ("R4",  "Resistor_SMD:R_0603_1608Metric",              88.00,   52.50, 0, True),
    ("R5",  "Resistor_SMD:R_0603_1608Metric",              84.20,   52.50, 0, True),
]

# Regiones donde gen_pcb.py empaqueta los pasivos que no estan anclados
# (los del DAC, el op-amp, la suma mono y el class-D: ~40 piezas de 0603).
# Dorso 100x60: esquivan las patas pasantes del frente (con 1mm de radio de
# pad), la franja de jacks (y<19 en x 25..75), el nucleo (x 32..68,
# y 21..49) y los bloques anclados de arriba.
FREE_REGIONS = [
    (20.0, 36.0, 31.0, 39.0),    # bajo DOWN, sobre el sensado de VBUS
    (26.5, 41.0, 31.0, 53.0),    # entre el sensado y el nucleo, sobre el slide
    (69.5, 44.0, 71.5, 59.0),    # columna entre Select y U4
    (94.5, 36.0, 99.0, 48.5),    # columna derecha, bajo J5
    (31.0, 49.0, 32.5, 59.0),    # columna entre el slide y U5
    (0.5, 48.0, 5.5, 59.0),      # margen izquierdo, al lado del USB
    (18.5, 0.5, 21.5, 12.0),     # sobre UP, entre el gatillo L y el opto
]

# Nucleo del RP2350A (rp_core.py): U1 en (x, y) del dorso, bloque a rot 90
# como en la placa de 80 (ruteo probado). A rot 90 el bloque ocupa
# x-21..x+15, y-16.5..y+11.5: con (53, 37.5) queda en x 32..68, y 21..49,
# detras del panel, la unica zona sin patas pasantes del frente.
NUCLEO = (53.0, 37.5, 90.0)
```

If the packer reports it could not place every passive (`gen_pcb.py` prints how many of how many it packed), widen the regions in this order: the column at x 69.5–71.5 can grow to x 72 once `check_placement` shows U4's pads; the strip under DOWN can reach y 35.75 + 1.


- [ ] **Step 4: Run tests, generate the board, run the placement check**

```bash
"$KIPY" tests/run_tests.py 2>&1 | grep -a "^Ran\|^OK\|FAIL"
"$KIPY" gen_pcb.py 2>&1 | grep -av swig | tail -8
"$KIPY" checks/check_placement.py 2>&1 | grep -av swig
```

Expected: tests `OK`; `gen_pcb.py` prints `empaquetados en el dorso: N de N pasivos` (N = everything not anchored) and `nucleo RP2350A copiado: 149 pistas, 28 vias, 7 zonas`; `check_placement.py` ends with `OK: sin solapamientos de pads y todo dentro de la placa.` If it reports J2's mouth facing inward, set J2's rotation to 0 and rerun. If it reports a pad overlap, move the named part by whole millimetres away from the other and rerun; never move front parts (Task 4 fixed them).

- [ ] **Step 5: Pre-route DRC**

```bash
"$KIPY" manual_tracks.py 2>&1 | grep -a "ERROR\|guardado"
"$KIPY" plane_vias.py 2>&1 | grep -a "guardado"
"$KICLI" pcb drc --severity-all --format json -o logs/drc_pre.json pikocore_gamepad.kicad_pcb > /dev/null
python -c "import json,collections;d=json.load(open('logs/drc_pre.json',encoding='utf-8'));print(collections.Counter((v['severity'],v['type']) for v in d['violations']))"
```

Expected: `manual_tracks.py` prints no `ERROR:` line (every manual track still lands on its pad: J2, U7 and U1 tracks are relative to `_POS`/`NUCLEO`); DRC errors other than `clearance`/`hole_clearance` of plane vias against the inner planes (those are the pre-fill artefact seen on the chip-down) must be 0. `courtyards_overlap` → move the named part and go back to Step 4.

- [ ] **Step 6: Commit**

```bash
git add placements.py tests/test_netlist.py pikocore_gamepad.kicad_pcb pikocore_gamepad.kicad_pro
git commit -m "hw: dorso de 100x60: jacks arriba, USB abajo-izq, nucleo detras del panel" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: Routing cycle to DRC clean

**Files:**
- Modify: `placements.py` only if a net cannot be routed (move the part, re-run Task 5 steps 4–5)
- Modify: `rp_core.py` `FANOUT_NETS` only if a U1 pin stays unrouted two cycles in a row
- Produces: `pikocore_gamepad.kicad_pcb` routed; `logs/drc.json` with 0 errors, 0 unconnected, 0 parity

- [ ] **Step 1: Create the cycle script**

Write `logs/ciclo.sh` (it is git-ignored under `logs/`):

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/.."
KIPY="/c/Program Files/KiCad/9.0/bin/python.exe"
KICLI="/c/Program Files/KiCad/9.0/bin/kicad-cli.exe"
JAR="$HOME/Documents/KiCad/10.0/3rdparty/plugins/app_freerouting_kicad-plugin/jar/freerouting-2.4.1.jar"
abiertas() { python -c "import json;print(len(json.load(open('logs/drc.json',encoding='utf-8'))['unconnected_items']))"; }
drc() { "$KICLI" pcb drc --severity-all --schematic-parity --format json -o logs/drc.json pikocore_gamepad.kicad_pcb > /dev/null || true; }
"$KIPY" gen_sch.py > /dev/null
"$KICLI" sch export netlist -o pikocore_gamepad.net pikocore_gamepad.kicad_sch
"$KIPY" gen_pcb.py 2>&1 | grep -av swig | tail -3
"$KIPY" manual_tracks.py 2>&1 | grep -a "ERROR" && exit 1
"$KIPY" plane_vias.py 2>&1 | grep -a guardado
"$KIPY" route_io.py export 2>&1 | grep -a protegidas
java -Djava.awt.headless=true -jar "$JAR" -de pikocore_gamepad.dsn -do pikocore_gamepad.ses -mp 60 -mt 1 -l en > logs/freerouting.log 2>&1 || true
"$KIPY" route_io.py import 2>&1 | grep -a "SES import"
"$KIPY" finish_pcb.py 2>&1 | grep -a "guardado"
drc; N1=$(abiertas); echo "pasada 1: $N1 abiertas"
cp pikocore_gamepad.kicad_pcb logs/pass1.kicad_pcb; cp logs/drc.json logs/drc_pass1.json
"$KIPY" route_io.py repaso 2>&1 | grep -a protegidas
java -Djava.awt.headless=true -jar "$JAR" -de pikocore_gamepad.dsn -do pikocore_gamepad.ses -mp 30 -mt 1 -l en > logs/freerouting2.log 2>&1 || true
"$KIPY" route_io.py import > /dev/null 2>&1; "$KIPY" finish_pcb.py > /dev/null 2>&1
drc; N2=$(abiertas); echo "pasada 2: $N2 abiertas"
if [ "$N2" -ge "$N1" ]; then cp logs/pass1.kicad_pcb pikocore_gamepad.kicad_pcb; cp logs/drc_pass1.json logs/drc.json; echo "pasada 2 descartada"; fi
python ../../../.claude/skills/pcb-verify/scripts/read_drc.py logs/drc.json
```

- [ ] **Step 2: Run it in the background (about 40 minutes) and wait for it**

```bash
bash logs/ciclo.sh > logs/ciclo.log 2>&1 &
```

Then wait with a background `until grep -q "Veredicto" logs/ciclo.log; do sleep 30; done`. Do not start a second cycle while one runs: both write the same files (this happened twice on the chip-down and corrupted a run).

- [ ] **Step 3: Read the result**

```bash
tail -n 12 logs/ciclo.log
python -c "import json;d=json.load(open('logs/drc.json',encoding='utf-8'));[print(v['type'],[(i['description'][:70],i['pos']) for i in v['items']]) for v in d['violations'] if v['severity']=='error'];[print('UNC',[(i['description'][:70],i['pos']) for i in v['items']]) for v in d['unconnected_items']]"
```

Decide by what is left:
- **Unconnected on a U1 pin** two cycles in a row → add that net to `rp_core.FANOUT_NETS` (the copied RP escape lane) and rerun.
- **Unconnected elsewhere** → the two parts are boxed in by THT legs; move the smaller one 2–3 mm toward open area in `placements.py`, rerun Task 5 steps 4–5, rerun the cycle.
- **`hole_to_hole` / `annular_width` errors** → `route_io.py import` already fixes short rings; a `hole_to_hole` between a plane via and a thermal via means `plane_vias.py` placed a via on an exposed pad — already excluded for U7/U1; if it names another part, add it to the same exclusion (the `any(q.GetNumber() == pad.GetNumber() and q.GetAttribute() == PTH ...)` check in `pads_sin_plano`).
- **`clearance` of a Power via against a Default track** → Power clearance is already 0.127; this should not appear. If it does, report it instead of tuning rules.

Repeat until `0 errores` and `unconnected_items: 0`. Keep a count; if the fourth cycle still has open nets, stop and report which, with the plot from `logs/`.

- [ ] **Step 4: Commit the routed board**

```bash
git add pikocore_gamepad.kicad_pcb placements.py rp_core.py
git commit -m "hw: ruteo de la placa 100x60 con MIDI (DRC 0 errores, 0 sin conectar)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: Gates, fab package, DXF template, docs

**Files:**
- Modify: `hardware/pikocore_gamepad/README.md`
- Modify: the spec (Not verified section)
- Regenerate: `pikocore_gamepad_template.dxf`, `fab/`

- [ ] **Step 1: Run every gate**

```bash
"$KIPY" tests/run_tests.py 2>&1 | grep -a "^Ran\|^OK\|FAIL"
"$KIPY" checks/run_all.py 2>&1 | grep -av swig | tail -6
"$KICLI" sch erc --severity-all --exit-code-violations -o logs/erc.rpt pikocore_gamepad.kicad_sch; echo "erc exit $?"
"$KICLI" pcb drc --severity-all --schematic-parity --exit-code-violations --format json -o logs/drc.json pikocore_gamepad.kicad_pcb; echo "drc exit $?"
python ../../../.claude/skills/pcb-verify/scripts/read_drc.py logs/drc.json | grep -a "violations\|unconnected\|parity\|error"
"$KIPY" gen_fab.py --force 2>&1 | grep -a "FALTAN\|zip\|^   "
"$KIPY" gen_template_dxf.py 2>&1 | grep -av swig | tail -2
python ../../../.claude/skills/pcb-verify/scripts/check_freshness.py . | tail -4
```

Expected: tests `OK`; `run_all.py` lists only `G-0` as failing (LCD_FPC_PIN_ORDER); ERC exit 0; DRC exit 0 with 0 errors / 0 unconnected / 0 parity; `gen_fab.py` lists blanks for `10R`, `33R`, `220R`, `74LVC1G17`, `H11L1M`, `1N4148W` plus the pre-existing hand-soldered THT lines; the DXF regenerates for 100 × 60; G-F reports only the `NO-FABRICABLE` zip name mismatch (as on the chip-down) or nothing.

- [ ] **Step 2: Render both sides**

```bash
for s in top bottom; do "$KICLI" pcb render --side $s --width 1800 --height 1440 --quality high -o logs/render_$s.png pikocore_gamepad.kicad_pcb > /dev/null; done
```

Open `logs/render_bottom.png` and check by eye: three jack barrels crossing the top edge between the shoulder tacts, USB-C mouth crossing the bottom edge, nothing hanging outside the outline but those and the slide switch actuator.

- [ ] **Step 3: Update the README**

In `hardware/pikocore_gamepad/README.md`, insert before the `**Branch hw/chipdown-rp2350 (2026-10-15)...**` paragraph:

```markdown
**Branch `hw/chipdown-rp2350`, second step (2026-10-15): Game Boy Micro layout,
100 × 60 mm, with MIDI.** Screen in the centre (active area centred at
x 50, y 24), D-pad cross on the left, X/Y/A/B diamond on the right, Select
and Start under the diamond, L/R shoulder tacts in the top corners.
Phones, MIDI IN and MIDI OUT are 3.5 mm TRS jacks on the top edge (back
side); MIDI is type A on UART1 (GP24 TX, GP25 RX, `PIN_MIDI_TX`/`PIN_MIDI_RX`
in `config.h`), 3.3 V output resistors through a 74LVC1G17, H11L1 opto input.
`VBUS_SENSE` moved to GP27. Spec and open items:
[`docs/superpowers/specs/2026-10-15-pikocore-gamepad-micro-layout-midi-design.md`](../../docs/superpowers/specs/2026-10-15-pikocore-gamepad-micro-layout-midi-design.md).
Gates as below; G-0 red only for `LCD_FPC_PIN_ORDER`. Not verified: U9/U10
pinouts against their datasheets (marked SIN VERIFICAR in the schematic),
LCSC codes for the MIDI parts, the enclosure for 100 × 60.
```

- [ ] **Step 4: Update the spec's "Not verified" section**

Replace its bullet list with the actual state after Task 7: which pinouts are still unverified, which LCSC codes are blank (from the `gen_fab.py` output), and that no board has been built. Keep the enclosure bullet.

- [ ] **Step 5: Commit**

```bash
git add ../README.md pikocore_gamepad_template.dxf fab/ logs/.gitkeep 2>/dev/null; git add -A ../ ../../../docs/superpowers/specs/2026-10-15-pikocore-gamepad-micro-layout-midi-design.md
git status --short   # only the files above plus regenerated schematics/board; no logs/*.png
git commit -m "hw: puertas, paquete de fab y docs de la placa 100x60 con MIDI" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

Do not push.
