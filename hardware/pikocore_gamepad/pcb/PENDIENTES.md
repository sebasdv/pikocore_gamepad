> ⚠️ **Documento histórico, heredado del fork.** Describe el proyecto GAMESETUP
> original (`C:\midigame\GAMESETUP`), no `pikocore_gamepad`. Las rutas de archivo
> de aquí abajo (`gamesetup.kicad_pro`, `gamesetup.net`, etc.) apuntan al proyecto
> viejo, en su repo aparte — **no** a este fork. Se conserva por el research de
> partes que sigue aplicando (jack de audio V-3, fuerza de los tacts, etc.), no
> como instrucciones operativas para este proyecto. Ver
> `docs/superpowers/plans/2026-08-11-pikocore-gamepad-pcb-fork.md` para el estado
> real de este fork.

# GAMESETUP V2 — pendientes

Estado al **2026-08-08**, rama `GAMESETUPV2`, último commit `8f55abb`.

## Dónde está todo

```
C:\midigame\GAMESETUP\pcb\gamesetup.kicad_pro      ← abrí este en KiCad
```

Setup de una sesión de trabajo:

```bash
export KIPY="$LOCALAPPDATA/Programs/KiCad/9.0/bin/python.exe"
export KICLI="$LOCALAPPDATA/Programs/KiCad/9.0/bin/kicad-cli.exe"
cd C:/midigame/GAMESETUP/pcb
```

## Cómo está la placa hoy

| | |
|---|---|
| Esquemático | 91 componentes, 87 nets — **ERC 0 errores, 0 avisos** |
| Placa | 4 capas, 90 × 130 mm, **sin rutear** (ver punto 5) |
| Reparto | 69 piezas SMD que monta JLC · 22 THT |
| Tests | 215 en verde |
| G-2 netlist | 351 conexiones idénticas esquemático ↔ PCB |
| Placement | sin solapamientos, todo dentro de placa |
| **G-0 fabricación** | **BLOQUEADA**: 7 constantes sin medir, 7 footprints provisionales |

`gen_pcb.py` regenera la placa desde cero cada vez que corre. Lo que se toca a
mano en la GUI se pierde: las posiciones van por el ciclo DXF y el netlist por
`netlist.py`.

---

# 1. Medir el módulo LCD con calibre

Son dos números y cierran dos tareas de verificación. El módulo lo tenés.

| Qué medir | Constante | Valor provisional |
|---|---|---|
| Borde superior del módulo → **centro de la fila de pines** | `LCD_PIN_ROW_Y` | 1.60 mm |
| Borde del módulo → **centro del agujero**, en los dos ejes | `LCD_HOLE_INSET` | 2.19 mm |

**Hipótesis sobre el segundo, para que sepas qué esperar:** la cota del drawing
dice 2.19 y la nota china dice 2.5, y puede que no se contradigan sino que
acoten cosas distintas — `(27.78 − 23.40)/2 = 2.19` **exacto**, o sea que 2.19
sería el margen lateral del área activa y 2.5 el centro del agujero. Si es así,
el valor correcto es **2.5**.

Editar en `params.py`, poner `verified=True` y anotar en `note` cómo se midió.

```bash
python checks/check_verified.py     # debería bajar de 7 a 5 constantes
python tests/run_tests.py
```

---

# 2. Elegir las partes que faltan en LCSC

Cada una bloquea G-0 mientras su footprint sea provisional.

### 2.1 Jack de audio — el más delicado

Requisitos **en orden**: THT · 3.5 mm estéreo · contacto NC aislado ·
**datasheet público descargable**.

El cuarto es el que descartó al `PJ-320A` de V1: LCSC bloquea su datasheet con
un 403 y nunca se pudo verificar qué pin es cuál. Candidato primario **CUI
SJ1-3535NG**; alternativa la familia **PJ-313D**.

Hace falta el código LCSC **y** el mapeo pin → función (tip / ring / sleeve /
detección).

### 2.2 Tact vertical 6×6 THT — 10 unidades

Buscá **100–160 gf** de fuerza de actuación. El de V1 era de 260 gf y por eso
se cambió: con patrones rápidos, 260 cansa.

**Atajo posible:** KiCad ya trae `Button_Switch_THT:SW_PUSH_6mm` (pads en
4.5 × 6.5 mm, la geometría estándar del 6×6). Si la parte que elegís coincide,
`BTN_FP` deja de ser provisional sin importar nada.

### 2.3 Tact angulado para L y R — 2 unidades

El footprint ya está resuelto: `SW_Tactile_SPST_Angled_PTS645Vx39-2LFS`, que
viene con KiCad. Falta el número de parte concreto.

**El largo del actuador se decide con el enclosure, no ahora**: las variantes
`Vx31/39/58/83` comparten **exactamente la misma geometría de pads**, así que
cambiar de una a otra no toca la PCB.

⚠️ Tiene **2 pines eléctricos**, no 4. Los otros dos contactos son patas de
anclaje mecánico (taladro 1.30 mm). Si comprás un angulado de 4 pines, avisame:
cambia el símbolo.

### 2.4 Jacks TRS 3.5 mm THT para MIDI — 2 unidades

Solo 3 conductores, sin contacto de detección. Pueden ser el mismo modelo que
el de audio si ese tiene 3 pines usables.

### 2.5 Socket microSD push-push — 1 unidad

El pinout **varía entre fabricantes**. Hace falta el código **y el datasheet**.

### 2.6 Op-amp en SOIC-8 — ⚠️ el código que diste quedó obsoleto

`C2838125` es el **NJM4556AD en DIP-8**. Al pasar a SMD hace falta la versión
**SOIC-8** (`NJM4556AM` o equivalente), que es otra parte.

### 2.7 Optoacoplador SMD — ⚠️ ídem

`C78588` es el **H11L1 en DIP-6**. Hace falta la versión SMD (`H11L1S` /
`H11L1SM`) en encapsulado **SO-6**.

**Si no aparece con stock**, el fallback es el **6N137 en SOIC-8** — pero ese
**cambia el símbolo**: 8 pines y otro pinout. No es un cambio de una línea.

---

# 3. Calcular el lazo del boost (V-7)

Desde la hoja de datos del **TPS61023**, para 5 V de salida con el consumo del
op-amp:

| Constante | Provisional | Qué es |
|---|---|---|
| `BOOST_L` | 2.2 µH | inductor |
| `BOOST_RFB_TOP` | 1000 kΩ | divisor de realimentación, arriba |
| `BOOST_RFB_BOT` | 200 kΩ | divisor, abajo |

El **encapsulado del inductor sí está confirmado** por el part number
(`CKST322512` → 3225 métrico = 1210 imperial), así que solo cambia el valor.

Verificar además que la corriente de salida cubra el consumo del NJM4556AD con
margen.

---

# 4. Confirmar el encapsulado del PCF8574

El sufijo **`MT`** de `PCF8574MT/TR` es de HGSEMI, no de TI (que usa `PW` para
TSSOP-16). Confirmar en la ficha de LCSC que sea **TSSOP-16 de 4.4 × 5 mm,
paso 0.65** — es el footprint asumido.

**Por qué importa tanto:** es exactamente el mismo tipo de error que el
TPS61023, donde el sufijo `DRL` reveló que era SOT-563 y no SOT-23-6. Un
footprint equivocado no lo detecta ninguna puerta — el DRC valida geometría
contra geometría, nunca contra la pieza real.

---

# 5. Re-rutear

**La placa en disco no tiene pistas.** El ruteo anterior quedó obsoleto al
cambiar los gatillos a angulados y el op-amp/opto a SMD.

Conviene hacerlo **después** de cerrar los puntos 1 y 2: los footprints
definitivos cambian la geometría y el ruteo habría que rehacerlo igual.

```bash
"$KIPY" gen_pcb.py
"$KIPY" route_io.py export
java -jar "$TEMP/freerouting.jar" -de gamesetup.dsn -do gamesetup.ses -mp 50
"$KIPY" route_io.py import
"$KIPY" finish_pcb.py
"$KICLI" pcb drc --severity-all --format json gamesetup.kicad_pcb -o logs/drc.json
```

**Qué esperar.** La última corrida dio **0 errores de cobre** (sin
cortocircuitos, sin violaciones de margen ni de orificio) con **9 conexiones
sin cerrar de 355** — o sea 97.5%. La placa es ruteable; lo que falta son
artefactos de redondeo de freerouting, que es estocástico: dos corridas dieron
8 y 9 con culpables distintos. Repetir el ciclo es la salida documentada.

**Trampas ya conocidas, para no perder tiempo:**

- **No pasar `route_io.py` ni `kicad-cli` por `| grep`.** El assert de
  "non-closed outline" y el memory-leak de SWIG salen por stderr y hacen
  deadlock del pipe: parece colgado. Redirigir a un log y grepear el archivo.
- **No lanzar freerouting con `nohup ... &` dentro de un comando en
  background**: el shell retorna de inmediato y se lleva a java. Lanzarlo
  directo.
- **No agregar vías de stitching.** Se probó: con GND en un plano interno y sin
  vertido en las capas externas, no conectan nada — 21 de 24 salieron
  `via_dangling` y dos causaron cortocircuitos reales.

---

# 6. Generar fabricación

Solo cuando G-0 pase.

```bash
"$KIPY" checks/run_all.py     # G-0, G-5, G-4, G-2 y placement
"$KIPY" gen_fab.py            # ← todavía NO existe, hay que escribirlo
```

`gen_fab.py` es lo único del plan que falta escribir (Task 19): gerbers de las
4 capas, drill, BOM y CPL para JLCPCB, con G-0 como puerta previa.

---

# Verificaciones que ya están cerradas

Para no repetir trabajo:

- **Pinouts del PCM5102A, NJM4556AD, PAM8302A y el nav WS-1004** — verificados
  en V1 contra datasheet, y llegaron a una placa ruteada. Hay tests que impiden
  que alguien los reescriba de memoria.
- **Cotas del LCD que cierran por aritmética exacta**: ancho, alto, posición del
  pin 1, área activa, márgenes del vidrio. No dependen del calibre.
- **Pinout PCB ↔ firmware** (`boards/rp2350plus_v2/config.h`): 20 pines, puerta
  G-4, probada por mutación en tres direcciones.
- **El contorno de la placa** ya no deriva entre ciclos de Rhino.

# Si movés algo en Rhino

```bash
"$KIPY" gen_template_dxf.py                        # genera el template
# ... editar en Rhino, guardar como gamesetup_template_MOD.dxf ...
python parse_dxf.py gamesetup_template_MOD.dxf     # dry run, no toca nada
python parse_dxf.py gamesetup_template_MOD.dxf --write
"$KIPY" gen_pcb.py
"$KIPY" checks/check_placement.py
```

**La rotación no viaja por el DXF** — una cruz no tiene orientación. Se edita a
mano en `placements.py`. Importa sobre todo para los gatillos L y R, donde la
rotación define hacia dónde apunta el actuador (`rot 90` = izquierda,
`rot 270` = derecha).
