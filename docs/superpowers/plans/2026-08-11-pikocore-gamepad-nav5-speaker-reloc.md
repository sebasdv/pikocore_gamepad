# pikocore_gamepad PCB — NAV5 D-pad + Speaker Relocation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the D-pad's 4 discrete tact switches with a single 5-way NAV5
switch (mirrored with the X/Y/A/B diamond, center wired as `BTN_OK`), relocate the
speaker connector `J5` next to the RP2350-Plus module, and shrink the provisional
board height accordingly — implementing
[2026-08-11-pikocore-gamepad-nav5-speaker-reloc-design.md](../specs/2026-08-11-pikocore-gamepad-nav5-speaker-reloc-design.md).

**Architecture:** Same forked pipeline as before
(`docs/superpowers/plans/2026-08-11-pikocore-gamepad-pcb-fork.md`): `pinmap.py` is
authoritative for GPIO assignment, `netlist.py` derives the schematic's MCU nets from
it via `_mcu_nets()`, `placements.py` holds PCB positions independently. This plan
touches all three plus `params.py` (board height), the pinout doc, the firmware
pin-map stub, and their corresponding tests — then regenerates and re-verifies the
whole pipeline as the final task.

**Tech Stack:** Same as the fork plan — Python 3.11, KiCad 9.0
(`$LOCALAPPDATA/Programs/KiCad/9.0/bin/`) for anything importing `pcbnew` or running
`kicad-cli`.

---

### Task 1: Assign `BTN_OK` a GPIO and update every pin-map-derived file

**Files:**
- Modify: `hardware/pikocore_gamepad/pcb/pinmap.py`
- Modify: `hardware/pikocore_gamepad/pcb/firmware_pin_stub/config.h`
- Modify: `hardware/pikocore_gamepad/pcb/tests/test_pinmap.py`
- Modify: `docs/hardware/pikocore_gamepad-pinout.md`

- [ ] **Step 1: Add `BTN_OK` to `pinmap.py`'s `GPIO` dict, shrink `FREE`**

In `hardware/pikocore_gamepad/pcb/pinmap.py`, change:

```python
    22: "DAC_XSMT",    # pulldown 100k: arranca muteado
}

# Sin MIDI, sin microSD, sin expansores I2C: no queda nada que enrutar por
# expansion salvo estos 3, con ADC.
FREE = (26, 27, 28)
```

to:

```python
    22: "DAC_XSMT",    # pulldown 100k: arranca muteado
    26: "BTN_OK",      # centro del NAV5
}

# Sin MIDI, sin microSD, sin expansores I2C: no queda nada que enrutar por
# expansion salvo estos 2, con ADC.
FREE = (27, 28)
```

- [ ] **Step 2: Run a quick sanity check**

```bash
cd hardware/pikocore_gamepad/pcb
python -c "import pinmap; print(len(pinmap.GPIO), pinmap.FREE)"
```

Expected: `24 (27, 28)`

- [ ] **Step 3: Add the matching `#define` to the firmware pin-map stub**

In `hardware/pikocore_gamepad/pcb/firmware_pin_stub/config.h`, change:

```c
#define PIN_DAC_XSMT     22
```

to:

```c
#define PIN_DAC_XSMT     22
#define PIN_BTN_OK       26
```

- [ ] **Step 4: Run gate G-4 to confirm the stub still matches**

```bash
python checks/check_pinmap.py
```

Expected: `OK: 24 pines coinciden entre PCB y firmware.`

- [ ] **Step 5: Update `test_pinmap.py`'s free-pin-count tests**

In `hardware/pikocore_gamepad/pcb/tests/test_pinmap.py`, change:

```python
    def test_quedan_exactamente_tres_pines_libres(self):
        # pikocore_gamepad no tiene microSD, MIDI ni expansor I2C: sin esos
        # tres consumidores, solo quedan los 3 GPIO con ADC reservados.
        self.assertEqual(len(pinmap.FREE), 3)
```

to:

```python
    def test_quedan_exactamente_dos_pines_libres(self):
        # GP26 ahora es BTN_OK (centro del NAV5): de los 3 GPIO con ADC que
        # quedaban reservados, solo 2 siguen libres.
        self.assertEqual(len(pinmap.FREE), 2)
```

and change:

```python
    def test_los_tres_pines_con_adc_quedan_libres(self):
        # GP26/27/28 son los unicos con ADC del header: deben quedar
        # disponibles en el header de expansion para un potenciometro futuro.
        for g in (26, 27, 28):
            self.assertIn(g, pinmap.FREE)
```

to:

```python
    def test_los_dos_pines_con_adc_restantes_quedan_libres(self):
        # GP26/27/28 son los unicos con ADC del header. GP26 ahora es BTN_OK;
        # GP27/28 deben seguir disponibles en el header de expansion.
        for g in (27, 28):
            self.assertIn(g, pinmap.FREE)

    def test_btn_ok_toma_el_gpio_26(self):
        self.assertEqual(pinmap.gpio_of("BTN_OK"), 26)
```

- [ ] **Step 6: Run the pinmap test file**

```bash
python -m unittest tests.test_pinmap -v
```

Expected: all tests pass (25 tests — was 20 before this task's 2 renames + 1 new
test net to +1).

- [ ] **Step 7: Update the pinout reference doc**

In `docs/hardware/pikocore_gamepad-pinout.md`, change the row:

```markdown
| GP22 | `DAC_XSMT` | DAC mute control (starts muted via 100k pulldown) |
| GP26, GP27, GP28 | — | Reserved, unconnected (battery voltage sense candidate) |
```

to:

```markdown
| GP22 | `DAC_XSMT` | DAC mute control (starts muted via 100k pulldown) |
| GP26 | `BTN_OK` | NAV5 center press (confirm/select) |
| GP27, GP28 | — | Reserved, unconnected (battery voltage sense candidate) |
```

- [ ] **Step 8: Commit**

```bash
git add hardware/pikocore_gamepad/pcb/pinmap.py hardware/pikocore_gamepad/pcb/firmware_pin_stub/config.h hardware/pikocore_gamepad/pcb/tests/test_pinmap.py docs/hardware/pikocore_gamepad-pinout.md
git commit -m "hw: assign BTN_OK (NAV5 center) to GP26"
```

---

### Task 2: Restore the NAV5 symbol, trim the D-pad, wire SW13

**Files:**
- Modify: `hardware/pikocore_gamepad/pcb/netlist.py`
- Modify: `hardware/pikocore_gamepad/pcb/tests/test_netlist.py`

- [ ] **Step 1: Restore the `NAV_WS1004` symbol definition**

In `hardware/pikocore_gamepad/pcb/netlist.py`'s `SYMS = {...}` dict, immediately
after the `"LCD_ST7789"` entry's closing `),` and before the `"SW_Push"` entry, add
back:

```python
    "NAV_WS1004": dict(
        ref="SW", w=7.62, h=12.7,
        desc="XUNPU WS-1004-ARL10026, nav switch de 5 vias THT 10.2x10.2mm. "
             "Pinout de datasheet: 1=COM 2=LEFT 3=CENTRO 4=UP 5=RIGHT 6=DOWN. "
             "Cada direccion cierra contra el comun (pin 1).",
        ds="https://www.lcsc.com/product-detail/C42377836.html",
        pins=_left_pins(["COM", "LEFT", "CENTER", "UP", "RIGHT", "DOWN"]),
    ),
```

This is the exact symbol GAMESETUP's history already had verified against the
part's datasheet (it was removed in the fork's Task 4 for an unrelated reason —
GAMESETUP used 2 of these for cursor navigation via I2C expanders, which
pikocore_gamepad doesn't have; the footprint file itself
(`lib/gamesetup_lcsc.pretty/SW-TH_WS-1004-ARL10026.kicad_mod`) was never deleted).

- [ ] **Step 2: Restore the `NAV_FP` footprint constant**

Find `BTN_RA_FP = "Button_Switch_THT:SW_Tactile_SPST_Angled_PTS645Vx39-2LFS"` and add
immediately after it:

```python
NAV_FP = "gamesetup_lcsc:SW-TH_WS-1004-ARL10026"
```

- [ ] **Step 3: Remove the D-pad from `TACTS`**

Change:

```python
TACTS = [
    ("SW1", "DPAD_UP"), ("SW2", "DPAD_DOWN"),
    ("SW3", "DPAD_LEFT"), ("SW4", "DPAD_RIGHT"),
    ("SW5", "BTN_X"), ("SW6", "BTN_Y"),
    ("SW7", "BTN_A"), ("SW8", "BTN_B"),
    ("SW11", "BTN_START"), ("SW12", "BTN_SELECT"),
]
```

to:

```python
TACTS = [
    ("SW5", "BTN_X"), ("SW6", "BTN_Y"),
    ("SW7", "BTN_A"), ("SW8", "BTN_B"),
    ("SW11", "BTN_START"), ("SW12", "BTN_SELECT"),
]
```

This alone removes `SW1`-`SW4` from `INSTANCES` too, since the block right below
(`# ------ tacts`) builds `SW_Push` instances from a list comprehension over
`TACTS` — nothing else needs editing for the D-pad's removal to take effect.

- [ ] **Step 4: Add the NAV5 instance**

Find the `# ------------------------------------------------- gatillos L y R (angulados)`
block (contains `SW9`/`SW10`) and add a new block right after its closing `]`:

```python
# ------------------------------------------------------------------- NAV5
# Reemplaza el D-pad de 4 tacts. Cablea directo al MCU (sin expansor: a
# diferencia de GAMESETUP, aca sobran GPIO). El comun (pin 1) va a masa; cada
# direccion, incluido el centro, a su propio GPIO con pull-up de firmware.
INSTANCES += [
    ("NAV_WS1004", "SW13", "NAV5", 300.0, 40.0, {
        "1": "GND", "2": "DPAD_LEFT", "3": "BTN_OK",
        "4": "DPAD_UP", "5": "DPAD_RIGHT", "6": "DPAD_DOWN"},
     {"LCSC": "C42377836", "FP": NAV_FP}),
]
```

- [ ] **Step 5: Run a quick sanity check**

```bash
python -c "import netlist; print('NAV_WS1004' in netlist.SYMS, [i[1] for i in netlist.INSTANCES if i[0]=='NAV_WS1004'])"
```

Expected: `True ['SW13']`

- [ ] **Step 6: Update `test_hay_doce_botones_en_total`**

In `hardware/pikocore_gamepad/pcb/tests/test_netlist.py`, change:

```python
    def test_hay_doce_botones_en_total(self):
        # 10 verticales mas los 2 gatillos angulados.
        vert = [i for i in netlist.INSTANCES if i[0] == "SW_Push"]
        ang = [i for i in netlist.INSTANCES if i[0] == "SW_Push_RA"]
        self.assertEqual(len(vert), 10)
        self.assertEqual(len(ang), 2)
        self.assertEqual(len(vert) + len(ang), 12)
```

to:

```python
    def test_hay_nueve_switches_fisicos(self):
        # 6 tacts verticales (X/Y/A/B + Start/Select) + 2 gatillos angulados
        # (L/R) + 1 NAV5 (reemplaza los 4 tacts del D-pad).
        vert = [i for i in netlist.INSTANCES if i[0] == "SW_Push"]
        ang = [i for i in netlist.INSTANCES if i[0] == "SW_Push_RA"]
        nav = [i for i in netlist.INSTANCES if i[0] == "NAV_WS1004"]
        self.assertEqual(len(vert), 6)
        self.assertEqual(len(ang), 2)
        self.assertEqual(len(nav), 1)
        self.assertEqual(len(vert) + len(ang) + len(nav), 9)

    def test_hay_trece_botones_logicos(self):
        # X/Y/A/B (4) + Start/Select (2) + L/R (2) + NAV5 (5: 4 direcciones +
        # BTN_OK) = 13, aunque solo sean 9 piezas fisicas.
        logicos = {sig for _, sig in netlist.TACTS}
        logicos |= {"BTN_L", "BTN_R"}
        logicos |= {"DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT", "BTN_OK"}
        self.assertEqual(len(logicos), 13)
```

- [ ] **Step 7: Restore `TestSimboloNav`**

The file currently has `class TestSimboloTact(unittest.TestCase):` immediately
followed later by `class TestSimboloSlide(unittest.TestCase):`. Before this task's
edit, the original (pre-fork-Task-4) ordering was `TestSimboloNav` → `TestSimboloTact`
→ `TestSimboloSlide`. Restore that ordering: insert the new class **immediately
before** `class TestSimboloTact(unittest.TestCase):`:

```python
class TestSimboloNav(unittest.TestCase):

    def test_tiene_seis_pines(self):
        self.assertEqual(len(netlist.SYMS["NAV_WS1004"]["pins"]), 6)

    def test_sigue_el_pinout_del_datasheet(self):
        # WS-1004-ARL10026: 1=COM 2=LEFT 3=CENTRO 4=UP 5=RIGHT 6=DOWN.
        self.assertEqual(pin_names("NAV_WS1004"),
                         ["COM", "LEFT", "CENTER", "UP", "RIGHT", "DOWN"])


class TestSimboloTact(unittest.TestCase):
```

(i.e. add the new class + a blank line, then the existing `class TestSimboloTact...`
line stays exactly as it already reads — this is a pure insertion, don't change
anything inside `TestSimboloTact` itself.)

- [ ] **Step 8: Add a NAV5 instance-wiring test**

In `TestInstanciasEntrada` (the class containing `test_hay_nueve_switches_fisicos`
from Step 6), add:

```python
    def test_el_comun_del_nav5_va_a_masa(self):
        self.assertEqual(nets_of("SW13")["1"], "GND")

    def test_el_nav5_cablea_las_5_direcciones_correctas(self):
        # Las 4 direcciones ya estaban en el pinmap desde el fork original
        # (heredadas del D-pad); BTN_OK es nuevo en este plan.
        n = nets_of("SW13")
        self.assertEqual(n["2"], "DPAD_LEFT")
        self.assertEqual(n["3"], "BTN_OK")
        self.assertEqual(n["4"], "DPAD_UP")
        self.assertEqual(n["5"], "DPAD_RIGHT")
        self.assertEqual(n["6"], "DPAD_DOWN")

    def test_las_5_nets_del_nav5_existen_en_el_pinmap(self):
        # gpio_of() falla fuerte (KeyError) si la funcion no esta asignada:
        # esto verifica que las 5 nets del NAV5 tengan un GPIO real detras,
        # no un nombre que quedo mal escrito.
        for func in ("DPAD_LEFT", "BTN_OK", "DPAD_UP", "DPAD_RIGHT", "DPAD_DOWN"):
            pinmap.gpio_of(func)  # no debe lanzar KeyError
```

- [ ] **Step 9: Run the netlist test file**

```bash
python -m unittest tests.test_netlist -v
```

Expected: all tests pass. Count: was 85 before this task; this task removes 1 test
(`test_hay_doce_botones_en_total`), adds 2 in its place
(`test_hay_nueve_switches_fisicos`, `test_hay_trece_botones_logicos`), adds
`TestSimboloNav` (2 tests) back, and adds 3 instance-wiring tests
(`test_el_comun_del_nav5_va_a_masa`, `test_el_nav5_cablea_las_5_direcciones_correctas`,
`test_las_5_nets_del_nav5_existen_en_el_pinmap`) — net **+6**, so expect **91 tests,
0 failures**.

- [ ] **Step 10: Commit**

```bash
git add hardware/pikocore_gamepad/pcb/netlist.py hardware/pikocore_gamepad/pcb/tests/test_netlist.py
git commit -m "hw: replace D-pad with NAV5, wire center to BTN_OK"
```

---

### Task 3: Reposition NAV5 and the speaker connector in `placements.py`

**Files:**
- Modify: `hardware/pikocore_gamepad/pcb/placements.py`

- [ ] **Step 1: Remove the D-pad's 4 rows, add the NAV5 row**

Change:

```python
    # D-pad en diamante, abajo a la izquierda.
    ("SW1", "gamesetup_lcsc:SW-TH_4P-L4.5-W4.5-P3.00-LS5.5",  22.50, 100.00, 0, False),  # UP
    ("SW2", "gamesetup_lcsc:SW-TH_4P-L4.5-W4.5-P3.00-LS5.5",  22.50, 116.00, 0, False),  # DOWN
    ("SW3", "gamesetup_lcsc:SW-TH_4P-L4.5-W4.5-P3.00-LS5.5",  14.50, 108.00, 0, False),  # LEFT
    ("SW4", "gamesetup_lcsc:SW-TH_4P-L4.5-W4.5-P3.00-LS5.5",  30.50, 108.00, 0, False),  # RIGHT
```

to:

```python
    # NAV5 (reemplaza el D-pad de 4 tacts): espejado con el diamante X/Y/A/B,
    # mismo eje Y=83. Ver spec 2026-08-11-pikocore-gamepad-nav5-speaker-reloc-design.md.
    ("SW13", "gamesetup_lcsc:SW-TH_WS-1004-ARL10026",     22.50,  83.00, 0, False),
```

- [ ] **Step 2: Relocate the speaker header**

Change:

```python
    # Parlante abajo a la izquierda.
    ("J5",  "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
     12.00, 124.00, 0, True),
```

to:

```python
    # Parlante: header en el dorso, junto al hueco que deja U1 (el modulo
    # RP2350-Plus tiene sus pines en dos filas laterales, con espacio libre
    # en el medio). El parlante fisico se atornilla al enclosure del lado del
    # FRENTE, sobre esta misma zona X/Y — no hace falta reservar espacio
    # aparte cerca del borde inferior. Exacta posicion relativa a los pines
    # de U1 se termina de ajustar en el pase de Rhino; si check_placement.py
    # reporta un choque de pads, correr este mismo layout con la Y de J5
    # movida +-5mm hasta que limpie.
    ("J5",  "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
     18.00,  30.00, 0, True),
```

- [ ] **Step 3: Run a quick sanity check**

```bash
python -c "import placements; refs={p[0] for p in placements.PLACEMENTS}; print(sorted(refs))"
```

Expected: `['J1', 'J4', 'J5', 'SW10', 'SW11', 'SW12', 'SW13', 'SW15', 'SW5', 'SW6', 'SW7', 'SW8', 'SW9', 'U1', 'U2', 'U3', 'U4', 'U5']` — 18 refs (the 21 from the fork plan, minus `SW1`-`SW4`, plus `SW13`).

- [ ] **Step 4: Commit**

```bash
git add hardware/pikocore_gamepad/pcb/placements.py
git commit -m "hw: place NAV5 mirrored with X/Y/A/B, move speaker header next to U1"
```

---

### Task 4: Shrink the provisional board height

**Files:**
- Modify: `hardware/pikocore_gamepad/pcb/params.py`

- [ ] **Step 1: Reduce `BOARD_H`**

Change:

```python
    "BOARD_H": Param(
        130.0, False,
        "PROVISIONAL: ver BOARD_W.",
        "V-0"),
```

to:

```python
    "BOARD_H": Param(
        105.0, False,
        "PROVISIONAL: ver BOARD_W. Bajado de 130 a 105 al mover el D-pad a "
        "NAV5 (Y=83, mas arriba que el viejo D-pad en Y=100-116) y J5 junto "
        "a U1 — ya no hace falta espacio cerca del borde inferior. Sigue "
        "siendo un placeholder: el contorno definitivo lo dibuja el usuario "
        "en Rhino.",
        "V-0"),
```

- [ ] **Step 2: Run a quick sanity check**

```bash
python -c "from params import v; print(v('BOARD_W'), v('BOARD_H'))"
```

Expected: `90.0 105.0`

- [ ] **Step 3: Commit**

```bash
git add hardware/pikocore_gamepad/pcb/params.py
git commit -m "hw: shrink provisional BOARD_H 130->105mm after D-pad/speaker relocation"
```

---

### Task 5: Regenerate, run the full check pipeline, and ERC

**Files:**
- Modify: none (verification + generated artifacts only)

- [ ] **Step 1: Regenerate the schematic**

```bash
cd hardware/pikocore_gamepad/pcb
python gen_sch.py
```

Expected: exits 0, overwrites `pikocore_gamepad.kicad_sch`/`.kicad_sym`. If it errors,
investigate before continuing — don't guess a fix blind.

- [ ] **Step 2: Export the netlist and regenerate the PCB**

```bash
"$LOCALAPPDATA/Programs/KiCad/9.0/bin/kicad-cli.exe" sch export netlist \
  --output pikocore_gamepad.net pikocore_gamepad.kicad_sch
"$LOCALAPPDATA/Programs/KiCad/9.0/bin/python.exe" gen_pcb.py
```

Expected: exits 0, reports the new board dimensions (90×105mm) and a footprint/net
count consistent with 9 physical switches instead of 12 (one fewer net-bearing
footprint tally to sanity-check by eye against the printed summary, not an exact
number to assert — `checks/run_all.py` in Step 3 is the real gate).

- [ ] **Step 3: Run the check gates**

```bash
"$LOCALAPPDATA/Programs/KiCad/9.0/bin/python.exe" checks/run_all.py
```

Expected: same pattern as the fork plan's final state — only gate **G-0** fails, and
its list of pre-existing provisional items is unchanged (this plan didn't resolve
GAMESETUP's inherited open part-sourcing questions, and `BOARD_H`'s new 105.0 value
is still `verified=False`, same provisional status as before, just a different
number). G-2 (netlist match), G-4 (pinmap, now 24/24), G-5 (dup refs), and the
placement-collision check must all show **0** issues. If the placement check reports
a pad collision involving `J5` or `SW13`, that's a real problem — nudge the offending
row's Y coordinate in `placements.py` by a few mm and re-run from Step 1, don't
suppress or skip the check.

- [ ] **Step 4: Run ERC**

```bash
"$LOCALAPPDATA/Programs/KiCad/9.0/bin/kicad-cli.exe" sch erc \
  --output logs/erc.log pikocore_gamepad.kicad_sch
```

Expected: 0 errors. Warnings should be exactly 2 now (`EXP_GP27`/`EXP_GP28` dangling
labels — `EXP_GP26` disappears since that pin is now `BTN_OK`, which is consumed by
`SW13`'s wiring). Any other warning needs investigation.

- [ ] **Step 5: Run the full test suite one more time**

```bash
cd /c/pikocore-main/hardware/pikocore_gamepad/pcb
python -m unittest discover tests
```

Expected: **181 tests, 0 failures** — 174 at the end of the fork plan, +1 from
`test_pinmap.py` (Task 1: 2 tests renamed with no count change, 1 new test added),
+6 from `test_netlist.py` (Task 2: -1/+2 on the button-count test, +2 for
`TestSimboloNav`, +3 for the NAV5 instance-wiring tests). If the actual count
differs, treat that as a real discrepancy to investigate — don't force-match by
deleting or skipping a test.

- [ ] **Step 6: Commit the evidence**

```bash
git add hardware/pikocore_gamepad/pcb/logs/erc.log hardware/pikocore_gamepad/pcb/pikocore_gamepad.kicad_sch hardware/pikocore_gamepad/pcb/pikocore_gamepad.kicad_sym hardware/pikocore_gamepad/pcb/pikocore_gamepad.kicad_pcb hardware/pikocore_gamepad/pcb/pikocore_gamepad.net
git commit -m "hw: pikocore_gamepad schematic/PCB regenerated — NAV5 + speaker reloc, checks green"
```

---

## Out of scope (tracked for future plans, not this one)

- The exact final `BOARD_H` value (105mm here is a reasoned placeholder, not a
  fabrication dimension — same status `BOARD_W` already has)
- Fine-tuning `J5`'s exact position relative to `U1`'s pin rows (Task 5, Step 3
  covers the collision-detection safety net; precise placement is a Rhino-layout
  task)
- PCB copper routing
- Everything already out of scope per the fork plan (enclosure, firmware repin, BOM
  purchase order, GAMESETUP's inherited part-sourcing items)
