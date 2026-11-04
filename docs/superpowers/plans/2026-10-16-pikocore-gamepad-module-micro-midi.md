# Micro layout (100 × 60) + TRS MIDI on the RP2350-Plus module — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the module-based pikocore_gamepad board on a 100 × 60 mm outline with the Game Boy Micro front layout, the RP2350-Plus soldered flat by its castellations, and MIDI IN/OUT on TRS type A, ending with DRC 0 errors / 0 unconnected / 0 parity.

**Architecture:** Start from `main` (module + 100 × 80). Most of the new content already exists, verified, on branch `hw/chipdown-rp2350`: the Micro front block of `placements.py`, the MIDI symbols/instances/tests, the firmware pin guards, and the routing-tool fixes (`route_io.py`, `finish_pcb.py`). Tasks bring those over with `git show hw/chipdown-rp2350:<path>` / `git checkout hw/chipdown-rp2350 -- <path>` and adapt them; the module footprint and the back layout are new.

**Tech Stack:** KiCad 9.0.1 Python (`$KIPY`), `kicad-cli` 9 (`$KICLI`), freerouting 2.4.1 headless, stdlib `unittest` via `tests/run_tests.py`, the Pico SDK build wrapper `C:\pkb\build.bat`. Git Bash on Windows.

**Spec:** `docs/superpowers/specs/2026-10-16-pikocore-gamepad-module-micro-midi-design.md`

## Global Constraints

- Work on branch `hw/modulo-micro-midi` (from `origin/main`). Commit after every task; push only when asked.
- Working directory for PCB commands: `hardware/pikocore_gamepad/pcb`. Set once per shell: `KIPY="/c/Program Files/KiCad/9.0/bin/python.exe"; KICLI="/c/Program Files/KiCad/9.0/bin/kicad-cli.exe"`.
- Outline 100 × 60 mm, 4 layers. Keep `main`'s netclass and via rules unless routing fails (spec: no QFN here).
- Module: 21.00 × 51.00 mm, soldered flat to the back by castellations, KiCad footprint `Module:RaspberryPi_Pico_SMD_HandSolder` derived without its 4 mounting NPTH and without pads D1–D3. Keep-out under it: 22.2 × 51 mm, **no through-hole tail and no SMD part**.
- Pico pin numbers stay (`pinmap.HEADER_ORDER`); pad 1 is at the USB-C end.
- MIDI: `MIDI_TX` = GP28, `MIDI_RX` = GP27, `FREE = ()`. MIDI TRS type A: Tip = DIN 5, Ring = DIN 4, Sleeve = DIN 2; output 33 Ω to 3V3 on Ring and 10 Ω from the 74LVC1G17 on Tip; input Ring → 220 Ω → H11L1 anode, Tip → cathode, 1N4148W anti-parallel, 4.7 kΩ pull-up, J6 sleeve unconnected.
- Placement of the module: centre (50.0, 33.0), USB-C end toward the bottom edge. Jacks: MIDI IN top-left band (x ≈ 30), MIDI OUT top-right band (x ≈ 69.5), phones jack on the left edge (barrel through x = 0, centre y ≈ 45).
- Never guess an LCSC code. Commit messages in Spanish, no accents, ending `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Shell gotcha: never pipe KiCad python's stderr through `grep` (SWIG floods it); redirect to a file in `logs/` and grep the file.

## Review Focus

1. **Module orientation:** if the USB-C end faces the top edge it is unreachable and collides with the jacks. Task 4 asserts pad 1 lands below the module centre, and the render is read by eye.
2. **Pad numbering:** a mirrored footprint swaps 3V3/VSYS/GND onto the wrong castellations. Task 3 tests pad coordinates against the Pico header order.
3. **Tails under the module:** a front tact tail under a flat module shorts or lifts it. Task 4 extends `check_placement.py` to flag any through-hole pad inside the module box.
4. **Firmware stubs on the new MIDI pins:** `hw_gamepi13.h` literals are invisible to G-4. Task 1 ports the test that checks them against `pinmap.py`.
5. **Battery plug:** the module's own BAT header is the only battery path and the user's cells are JST GH. No test can cover it; Task 7 writes it into the README so it is not lost.

---

### Task 1: Pin map, board height and firmware stubs

**Files:**
- Modify: `pcb/pinmap.py`, `pcb/params.py`, `src/boards/pikocore_gamepad/config.h`, `src/hw_gamepi13.h`, `src/main.cpp`
- Test: `pcb/tests/test_pinmap.py`, `pcb/tests/test_params.py`

**Interfaces:**
- Produces: `pinmap.GPIO[27] == "MIDI_RX"`, `pinmap.GPIO[28] == "MIDI_TX"`, `pinmap.FREE == ()`, `params.v("BOARD_H") == 60.0`, `PIN_MIDI_TX 28` and `PIN_MIDI_RX 27` in `config.h`, `GAMEPI_CLOCK_PIN`/`GAMEPI_TRIGO_PIN` = -1.

- [ ] **Step 1: Write the failing tests.** In `test_pinmap.py` replace the tests that assert `FREE` has 2 pins or that GP27/28 are free (lines ~38–56) with: `test_midi_usa_los_dos_pines_libres_del_modulo` (`GPIO[28] == "MIDI_TX"`, `GPIO[27] == "MIDI_RX"`, `FREE == ()`), `test_midi_tx_es_un_pin_tx_de_uart0` (`gpio_of("MIDI_TX") in UART0_TX_OK`), and the declared-pins test updated for the empty `FREE`. Port class `TestFirmwareStubs` from `git show hw/chipdown-rp2350:hardware/pikocore_gamepad/pcb/tests/test_pinmap.py`, changing its rule: every `GAMEPI_*_PIN` literal in the `PIKO_GAMEPAD` block must be `-1` or `25` (25 = the module's onboard LED, not on the header). In `test_params.py` add `test_la_placa_mide_100_por_60` (`BOARD_W == 100.0`, `BOARD_H == 60.0`).
- [ ] **Step 2: Run to verify they fail.** Run `"$KIPY" tests/run_tests.py > logs/t.log 2>&1; grep -a "^FAIL:\|^ERROR:\|^Ran" logs/t.log`. Expected: the new tests fail.
- [ ] **Step 3: Implement.** `pinmap.py`: add `27: "MIDI_RX"`, `28: "MIDI_TX"` to `GPIO`, `FREE = ()`, update the "Libres" comment and docstring. `params.py`: `BOARD_H` 60.0 (note: design choice, not a measurement). `config.h`: `#define PIN_MIDI_TX 28` / `PIN_MIDI_RX 27` with one-line comments (MIDI_RX is read by a PIO UART). `hw_gamepi13.h` (PIKO_GAMEPAD block): `GAMEPI_CLOCK_PIN -1`, `GAMEPI_TRIGO_PIN -1` with a comment saying why, LED stays 25. `main.cpp`: a pin of -1 means "not present" — guard every use: `CLOCK_PIN` (gpio_init/set_dir/pull ~1859–1872, `Onewiremidi_new` ~2014, `gpio_get` ~2984: treat as idle) and `TRIGO_PIN` (`output_trigger.Init` ~1934, `.Trigger()` ~997). Model the guards on `git show hw/chipdown-rp2350:src/main.cpp`.
- [ ] **Step 4: Run the tests and G-4.** Run the suite as in Step 2 (expected: only the netlist tests that still expect free pins GP27/28 may fail; list them, Task 2 owns them) and `"$KIPY" checks/check_pinmap.py > logs/g4.log 2>&1; tail -n 2 logs/g4.log`. Expected: `OK: ... pines coinciden`.
- [ ] **Step 5: Build the firmware.** Run `cmd //c "C:\pkb\build.bat C:\pkb\gp3 gp C:/pikocore_gamepad"` from `C:\pkb`. Expected: `BUILD OK` and a fresh `C:\pkb\gp3\pikocore.uf2`.
- [ ] **Step 6: Commit** `hw: placa de 100x60 y MIDI en GP27/GP28 (stubs del firmware apagados)`.

---

### Task 2: MIDI parts, sheet and tests

**Files:**
- Modify: `pcb/netlist.py`, `pcb/gen_sch.py`, `pcb/tests/test_netlist.py`
- Create (copy): `datasheets/SN74LVC1G17_SCES351Y.pdf`, `datasheets/H11L1M_rev1.0.7.pdf`

**Interfaces:**
- Consumes: Task 1's GPIO names.
- Produces: refs `J6, J7, U9, U10, D3, R40–R43, C56`; nets `MIDI_TX_BUF, MIDI_OUT_T, MIDI_OUT_R, MIDI_IN_R, MIDI_IN_A, MIDI_IN_K` (plus `MIDI_TX`, `MIDI_RX` from the pin map); sheet `07_midi`.

- [ ] **Step 1: Port the tests.** From `git show hw/chipdown-rp2350:.../tests/test_netlist.py` copy class `TestMidi` (all 9 tests, including the LCSC and the verified-pinout ones) into `tests/test_netlist.py`. Drop nothing: they apply as written.
- [ ] **Step 2: Run to verify they fail.** Run the module `tests.test_netlist.TestMidi`; expected: failures (missing refs).
- [ ] **Step 3: Port the netlist content** from `hw/chipdown-rp2350:pcb/netlist.py`: symbols `D_1N4148`, `H11L1`, `LVC1G17` (with their verified descriptions), `PINOUT_SIN_VERIFICAR = ()`, the MIDI `INSTANCES` block with its LCSC codes (C23140, C22859, C22962, C81598, C10425, C20082, plus C23162 and C14663 via `LCSC_PASIVOS`), and the `10R/33R/220R` entries of `LCSC_PASIVOS`. Copy the two datasheet PDFs with `git checkout hw/chipdown-rp2350 -- <path>`.
- [ ] **Step 4: Port the sheet** from `hw/chipdown-rp2350:pcb/gen_sch.py`: sheet `("07_midi", ..., ["J7","U9","R40","R41","J6","R42","D3","U10","R43","C56"], ["NOTA_MIDI"])` and the `NOTA_MIDI` text; in the root note change "cinco hojas" to "seis hojas" and add the MIDI mention.
- [ ] **Step 5: Regenerate and check.** Run `"$KIPY" gen_sch.py > logs/gs.log 2>&1`, `"$KICLI" sch export netlist -o pikocore_gamepad.net pikocore_gamepad.kicad_sch`, `"$KICLI" sch erc --severity-all --exit-code-violations -o logs/erc.rpt pikocore_gamepad.kicad_sch`; expected ERC exit 0 and `Errores0, Avisos 0`. Run the full suite; expected green except the placement/footprint tests Tasks 3–4 own.
- [ ] **Step 6: Commit** `hw: MIDI IN/OUT en TRS tipo A (hoja 07_midi, pinouts verificados)`.

---

### Task 3: Castellated module footprint

**Files:**
- Modify: `pcb/gen_fp.py`, `pcb/netlist.py` (U1 footprint and `MANUAL`), `pcb/gen_pcb.py` (3D model entry), `pcb/tests/test_netlist.py`
- Create: `pcb/lib/gamesetup_fp.pretty/RP2350-Plus_Castellated.kicad_mod` (generated)
- Delete: `pcb/lib/gamesetup_fp.pretty/RP2350-Plus_Socket.kicad_mod`

**Interfaces:**
- Produces: footprint id `gamesetup_fp:RP2350-Plus_Castellated` (pads `1..40` only, origin at the module centre, pad 1 at (−9.69, −24.13), pad 21 at (9.69, 24.13), pad 40 at (9.69, −24.13)); function `gen_fp.derivar_modulo_castellated() -> bool`.

- [ ] **Step 1: Write the failing tests** in a new class `TestModuloCastellated` in `tests/test_netlist.py`, reading the generated `.kicad_mod` as text: `test_tiene_los_pads_1_a_40_en_el_orden_del_header` (pad n for n ≤ 20 at y = −24.13 + 2.54·(n−1) with x < 0; pad n for 21 ≤ n ≤ 40 at y = 24.13 − 2.54·(n−21) with x > 0), `test_no_trae_agujeros_de_montaje_ni_pads_de_depuracion` (no `np_thru_hole`, no pad named `D1`, `D2` or `D3`), `test_u1_usa_la_huella_castellated_y_es_soldadura_manual` (U1 `FP == "gamesetup_fp:RP2350-Plus_Castellated"` and `MANUAL` true). Delete the module-height/J5 test (lines ~405–418 of the old file: it guarded against the socket's 8.5 mm) — the module no longer floats.
- [ ] **Step 2: Run to verify they fail.**
- [ ] **Step 3: Implement `derivar_modulo_castellated()`** in `gen_fp.py`, replacing `copiar_socket_de_v1`: read KiCad's `Module.pretty/RaspberryPi_Pico_SMD_HandSolder.kicad_mod` (KiCad 9 share path `C:/Program Files/KiCad/9.0/share/kicad/footprints`), remove the four `np_thru_hole` pads and the pads `D1`–`D3` by balanced-parenthesis block removal, set the model to `${KIPRJMOD}/lib/gamesetup_fp.3dshapes/RP2350-Plus_Module.step`, write the file, and call it from `main()`. `git rm` the socket footprint. Set U1's `FP` and `MANUAL` in `netlist.py`; rename the `MODELOS_PROPIOS` key in `gen_pcb.py` and set its offset to `(0, 0, 0.0)`.
- [ ] **Step 4: Generate and test.** Run `"$KIPY" gen_fp.py > logs/fp.log 2>&1` then the suite; expected green for these tests. Tune the STEP offset later by eye in a render (renders only).
- [ ] **Step 5: Commit** `hw: el modulo se suelda plano por castellations (huella oficial de la Pico sin agujeros de montaje)`.

---

### Task 4: Micro front and back placement

**Files:**
- Modify: `pcb/placements.py`, `pcb/checks/check_placement.py`, `pcb/tests/test_netlist.py`

**Interfaces:**
- Consumes: Task 3's footprint id; Task 2's refs.
- Produces: `placements.MODULE_POS == (50.0, 33.0)`, `placements.MODULE_BOX == (38.9, 7.5, 61.1, 58.5)`, `FREE_REGIONS` (rectangles on the back, outside `MODULE_BOX`).

- [ ] **Step 1: Write the failing tests** in `tests/test_netlist.py`: port `test_el_frente_es_la_disposicion_micro`, `test_todo_el_frente_cae_dentro_de_100x60` and the adapted shoulder-tact symmetry (bodies at 12 and 88, origins 9.75 and 85.75) from the chip-down branch; add `test_el_modulo_va_en_su_posicion_y_en_el_dorso` (U1 row at `MODULE_POS`, flip true), `test_nada_anclado_cae_dentro_del_modulo` (no back-anchored origin inside `MODULE_BOX`), `test_las_regiones_libres_no_pisan_el_modulo`, `test_los_jacks_estan_donde_dice_el_spec` (J6 origin x in 25–36, J7 x in 64–75, both y = 3.0; J1 origin x = 3.0, y in 40–50, rot 90 or 270), and keep `test_las_regiones_libres_caen_dentro_de_la_placa`.
- [ ] **Step 2: Run to verify they fail.**
- [ ] **Step 3: Rewrite `placements.py`.** Front block: copy from `git show hw/chipdown-rp2350:.../placements.py` (rows `LCD1` … `SW15`). Back: U1 at `MODULE_POS`; jacks as in Global Constraints; the audio chain (U5, U3, U4, C23/C24, bleeders), the TPS61023 boost cluster (rigid move, keep its relative geometry because `manual_tracks.py` ties tracks to it), J5 speaker header, MIDI parts (U10/R42/D3/R43/C56 beside J6; U9/R40/R41 beside J7), the jack-detect parts beside J1 — all placed in the free bands (left x 0.5–38 below the D-pad legs, right y 51–59 below the Select/Start legs, the 7 mm band y ≈ 36.1–42.9 between diamond and Select/Start for the 470 µF cans). Remove everything chip-down-specific that `main` never had. `FREE_REGIONS` rectangles avoid `MODULE_BOX` and tact tails. Coordinates are a starting hypothesis; `check_placement.py` and DRC arbitrate.
- [ ] **Step 4: Extend `check_placement.py`:** flag every `PAD_ATTRIB_PTH` pad whose centre lies inside `MODULE_BOX` (message `TACTO BAJO EL MODULO: <ref>.<pad>`), counted as a failure. Run `"$KIPY" gen_pcb.py > logs/gp.log 2>&1; "$KIPY" checks/check_placement.py > logs/cp.log 2>&1; tail -n 4 logs/cp.log`. Expected: `OK: sin solapamientos de pads y todo dentro de la placa.`; iterate on anchors until it is, and until `gen_pcb.py` reports every passive packed (no `AVISO ... sin lugar`).
- [ ] **Step 5: Check orientation and render.** Run a short pcbnew snippet that loads the board and prints `pad1.y > 33.0` for U1 (expected `True`); if `False`, change U1's rotation by 180 and rerun. Then `"$KICLI" pcb render --side bottom -o logs/render_bottom.png pikocore_gamepad.kicad_pcb` and read the image: the USB-C end faces the bottom edge, three jacks cross the outline as in the spec.
- [ ] **Step 6: Pre-route DRC.** Run `manual_tracks.py` and `plane_vias.py` (output to `logs/`), then `$KICLI pcb drc` to `logs/drc_pre.json`. Expected: no error except `clearance`/`hole_clearance` against inner-plane zones (pre-fill artefact) and nothing else; fix any `courtyards_overlap` by moving the named part.
- [ ] **Step 7: Commit** `hw: frente Micro y dorso con el modulo plano en 100x60`.

---

### Task 5: Routing tools and the committed cycle script

**Files:**
- Modify (replace from the chip-down branch): `pcb/route_io.py`, `pcb/finish_pcb.py`
- Create: `pcb/route_cycle.sh`

**Interfaces:**
- Produces: `route_io.py export|import|repaso`; `route_cycle.sh` (one full cycle: schematic → netlist → board → manual tracks → plane vias → export → freerouting → import → finish → DRC, with the second pass kept only if it leaves fewer open connections and skipped when the first leaves none; writes `logs/drc.json`).

- [ ] **Step 1: Bring the files over.** `git checkout hw/chipdown-rp2350 -- hardware/pikocore_gamepad/pcb/route_io.py hardware/pikocore_gamepad/pcb/finish_pcb.py`. They add `wx.DisableAsserts()` (the DSN export hangs on a modal wx dialog without it), protected pre-routed copper with a `logs/pre_ruteo.json` snapshot, the `repaso` command, and orphan-via removal. `blindar_zonas_externas` is harmless without core zones.
- [ ] **Step 2: Create `route_cycle.sh`** from the chip-down's untracked `logs/ciclo.sh` (still on disk under `pcb/logs/`): change its `cd` to the script's own directory, keep the lock directory and the file-based logging.
- [ ] **Step 3: Verify the export finishes.** Run `timeout 240 "$KIPY" route_io.py export > logs/export.log 2>&1; echo $?`. Expected: `0`, and `grep -a protegidas logs/export.log` prints a count. A non-zero exit or 124 means the wx dialog came back.
- [ ] **Step 4: Run the suite** (expected green) and **commit** `hw: herramientas de ruteo (asserts de wx, cobre protegido, ciclo versionado)`.

---

### Task 6: Route to DRC clean

**Files:**
- Modify: `pcb/placements.py` and `pcb/manual_tracks.py` only if a net cannot be routed.

- [ ] **Step 1: Run the cycle in the background.** `bash route_cycle.sh > logs/cycle.log 2>&1 &`, one cycle at a time (the lock directory refuses a second). A cycle takes up to ~40 minutes; wait on `until grep -aq "CICLO DONE" logs/cycle.log; do sleep 20; done`.
- [ ] **Step 2: Read the result.** `tail` the log and list the errors and the open items from `logs/drc.json`. Pass condition: `0 errores`, `unconnected_items: 0`, `schematic_parity: 0`.
- [ ] **Step 3: If nets are open,** decide by what is left. A net boxed in by tact tails → move the smaller part into open area and redo Task 4 Steps 4–6. A fine-pitch pin pair that freerouting leaves open in two cycles → hand-route it in `manual_tracks.py` relative to its footprint origin, measuring clearances against the pre-route board first (the chip-down's `logs/corridor.py` approach). Never tune rules to make a DRC error disappear. After four cycles with open nets, stop and report which, with a plot.
- [ ] **Step 4: Commit** the routed board and any placement or track changes: `hw: ruteo de la placa con modulo (DRC 0 errores, 0 sin conectar)`.

---

### Task 7: Gates, fab package, docs

**Files:**
- Modify: `hardware/pikocore_gamepad/README.md`, the spec's "Not verified" section; memory file `chipdown-descartado.md`.

- [ ] **Step 1: Run every gate.** Suite; `"$KIPY" checks/run_all.py` (only G-0 red, for `LCD_FPC_PIN_ORDER`); ERC exit 0; `$KICLI pcb drc --severity-all --schematic-parity` read with `.claude/skills/pcb-verify/scripts/read_drc.py` (0 errors, 0 unconnected, 0 parity); `"$KIPY" gen_fab.py --force`; `"$KIPY" gen_template_dxf.py` (contour 100 × 60); `check_freshness.py`. Expected: as stated; the fab package is named `NO-FABRICABLE` while G-0 is red.
- [ ] **Step 2: Render both sides** into `logs/` and read them: front per the Micro layout, back with the module flat and USB-C at the bottom edge.
- [ ] **Step 3: Update docs.** README: new "Current state" paragraph for this branch (what the board is, gates, what is not verified). Spec: replace "Not verified" with the real state — the Plus's castellation copper against the Pico footprint (1:1 paper check), the module's battery connector model versus the user's JST GH cells (**write the sentence: the carrier cannot reach the module's battery line, so the cells need a GH-to-MX1.25 pigtail or a re-crimped plug**), back-area closure result, PIO UART RX on GP27 as firmware work, enclosure items. Memory: edit `chipdown-descartado.md` to say the Micro + MIDI port to the module is done on `hw/modulo-micro-midi`.
- [ ] **Step 4: Commit** `hw: puertas, paquete de fab, DXF y docs de la variante con modulo`. Do not push.
