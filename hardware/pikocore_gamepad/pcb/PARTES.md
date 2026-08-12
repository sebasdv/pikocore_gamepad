> ⚠️ **Documento histórico, heredado del fork.** Describe las partes del
> proyecto GAMESETUP original — se conserva por el research de componentes
> (footprints verificados, decisiones de jack/tact/etc.) que este fork
> reutiliza, no como inventario de `pikocore_gamepad`. Ver
> `docs/hardware/pikocore_gamepad-pinout.md` y
> `docs/superpowers/plans/2026-08-11-pikocore-gamepad-pcb-fork.md` para el
> estado real de este proyecto.

# Partes de GAMESETUP V2

Estado de cada componente. **Verificado** significa: footprint importado y
revisado, y pinout confirmado contra datasheet o contra la pieza física.

## Heredados de V1 — verificados, sin trabajo pendiente

| Ref | Parte | LCSC | Footprint |
|---|---|---|---|
| U1 | Waveshare RP2350-Plus 16MB (socket 2×20) | — | `gamesetup_fp:RP2350-Plus_Socket` |
| U5 | PCM5102A TSSOP-20 | `C107671` | `gamesetup_lcsc:TSSOP-20_L6.5-W4.4-P0.65-LS6.4-BL` |
| U3 | NJM4556AD DIP-8 | `C2838125` | `gamesetup_lcsc:DIP-8_L8.8-W6.4-P2.54-LS7.6-BL` |
| U4 | PAM8302A MSOP-8 | `C113367` | `gamesetup_lcsc:MSOP-8_L3.0-W3.0-P0.65-LS5.0-BL` |
| SW13, SW14 | Nav switch XUNPU WS-1004-ARL10026 | `C42377836` | `gamesetup_lcsc:SW-TH_WS-1004-ARL10026` |
| SW15 | Slide SPDT SK12D07VG3 | `C431547` | `gamesetup_lcsc:SW-TH_SK12D07VG3` |

Pinouts que ya están confirmados y no hay que volver a verificar:

- **Nav switch WS-1004**, del datasheet: `1=COM 2=LEFT 3=CENTRO 4=UP 5=RIGHT 6=DOWN`.
  Cada dirección cierra contra el común.
- **NJM4556AD**, contra el símbolo de LCSC `C2838125`:
  `1=OUT1 2=IN1− 3=IN1+ 4=V− 5=IN2+ 6=IN2− 7=OUT2 8=V+`.
- **Slide SK12D07VG3**: pin 2 = común (centro), 1/3 = throws, 4/5 = patas de
  anclaje mecánico (van a GND).

## Resueltos en la segunda tanda (2026-08-01)

| Ref | Parte | Nº de parte | LCSC | Footprint |
|---|---|---|---|---|
| U10–U12 | PCF8574 ×3 | HGSEMI `PCF8574MT/TR` | `C22461594` | `Package_SO:TSSOP-16_4.4x5mm_P0.65mm` |
| U2 | Boost 5V | TI `TPS61023DRLR` | `C919459` | `Package_TO_SOT_SMD:SOT-563` |
| U6 | Optoacoplador MIDI IN | EVERLIGHT `H11L1` | `C78588` | `Package_DIP:DIP-6_W7.62mm` |
| L1, L2 | Inductor 2.2 µH | CENKER `CKST322512-2.2uH/M` | `C3002559` | `Inductor_SMD:L_1210_3225Metric` |
| D1 | Diodo de protección MIDI | JSMSEMI `1N4148W` | `C917030` | `Diode_SMD:D_SOD-123` |
| J5 | Header JST PH 2.0 ×2 | — | en mano | `Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical` |
| J7 | Header macho 1×9 | — | en mano | `PinHeader_1x09_P2.54mm_Vertical` |

### ⚠️ El TPS61023 NO es SOT-23-6

El sufijo `DRL` de TI significa **SOT-5X3 (SOT-563)**, no SOT-23-6 (que sería
`DBV`). El footprint estaba equivocado y la diferencia habría hecho la placa
inservible:

| | Pads | Paso |
|---|---|---|
| SOT-23-6 (lo que había) | 3.60 × 2.50 mm | 0.95 mm |
| SOT-563 (lo correcto) | 2.10 × 1.35 mm | 0.50 mm |

Corregido en `netlist.py`. **Ojo al soldar/ensamblar**: 0.50 mm de paso en un
cuerpo de 1.6 × 1.6 mm es la pieza más fina de la placa, más incluso que el
PCM5102A (0.65 mm). Va sí o sí por ensamblado de JLC.

### Pendiente de confirmar

- **Encapsulado del PCF8574MT.** El sufijo `MT` es de HGSEMI, no de TI (TI usa
  `PW` para TSSOP-16). Confirmar en la ficha de LCSC que sea TSSOP-16 de
  4.4×5 mm y paso 0.65 antes de fabricar. El footprint asumido es ese.
- **Valor del inductor.** Los 2.2 µH siguen siendo provisionales (**V-7**):
  hay que calcularlos desde la hoja de datos del TPS61023. El encapsulado
  1210/3225 sí está confirmado por el part number.

## Todavía sin elegir

| Ref | Parte | Cant | Qué falta |
|---|---|---|---|
| J1 | Jack audio 3.5 mm THT con contacto NC | 1 | **V-3**, ver abajo |
| SW1–SW12 | Tact 6×6 mm THT | 12 | modelo y fuerza de actuación (100–160 gf) |
| J2, J3 | Jack TRS 3.5 mm THT | 2 | 3 conductores, sin detección |
| J6 | Socket microSD push-push | 1 | el pinout varía entre fabricantes: hace falta el datasheet |

Fuera del netlist pero necesarios: **2 × header hembra 1×20** (el socket del
RP2350-Plus), **1 × header macho 1×7** (para el módulo LCD), el **parlante 8 Ω**
y la **batería LiPo** con conector PH1.25.

### Pinouts sin verificar

Los símbolos heredados de V1 traen su pinout confirmado contra datasheet y ya
llegaron a una placa ruteada. Los nuevos **no**, y su descripción lo dice —
`PINOUT SIN VERIFICAR` aparece en el PDF del esquemático, que es el mismo
mecanismo que V1 usó con el NJM4556AD antes de confirmarlo contra LCSC.

| Símbolo | Por qué falta verificar |
|---|---|
| `TPS61023` | Contra la hoja de datos de TI. |
| `H11L1` | Contra la hoja de datos de ON Semi. |
| `JACK_AUDIO` | La parte todavía no está elegida (**V-3**). |
| `JACK_TRS` | La parte todavía no está elegida (**V-4**). |
| `MICROSD` | El pinout varía entre fabricantes; la parte no está elegida (**V-4**). |

`netlist.PINOUT_SIN_VERIFICAR` es la lista ejecutable, y hay tests que verifican
que cada entrada exista como símbolo, que su descripción avise, y que **ningún
símbolo heredado de V1 aparezca en ella** — si uno aparece, es que alguien lo
reescribió y perdió la verificación.

### V-3 — el jack de audio

Requisitos, en orden: **THT · 3.5 mm estéreo · contacto NC aislado · datasheet
público descargable**.

El cuarto requisito es el que descarta al **PJ-320A** (`C2884926`) que quedó en
V1: LCSC bloquea su datasheet con un 403 y el símbolo de EasyEDA no trae nombres
funcionales, así que su mapeo pin→función nunca se pudo verificar. Además es
TRRS y no tiene switch aislado. Su footprint se **borró** de esta librería a
propósito, para que nadie lo reintroduzca por inercia.

Candidato primario: **CUI SJ1-3535NG** (CUI publica datasheets completos).
Fallback: familia PJ-313D.

Regla de decisión, para que la implementación no se bloquee: se toma el primero
de la lista que tenga datasheet descargable **y** stock LCSC ≥ 1000 unidades. Si
ninguno califica, escalar antes de dibujar el footprint.

## Estado de los modelos 3D

Tres footprints heredados de V1 **referencian un `.wrl` que no existe**:

| Footprint | Modelo faltante |
|---|---|
| `DIP-8_L8.8-W6.4-P2.54-LS7.6-BL` | `DIP-8_L8.8-W6.4-P2.54-LS7.6-BL.wrl` |
| `MSOP-8_L3.0-W3.0-P0.65-LS5.0-BL` | `MSOP-8_L3.0-W3.0-P0.65-LS5.0-BL.wrl` |
| `TSSOP-20_L6.5-W4.4-P0.65-LS6.4-BL` | `TSSOP-20_L6.5-W4.4-H1.0-LS6.4-P0.65.wrl` |

En V1 esas tres rutas apuntaban a `%TEMP%/fptest/t.3dshapes/`, un directorio
temporal que ya no existe — o sea que estaban rotas ahí también. Acá se
reapuntaron a la convención del proyecto
(`${KIPRJMOD}/lib/gamesetup_lcsc.3dshapes/`) **a propósito, aunque el archivo
falte**: una ruta correcta con el archivo ausente hace que KiCad avise, mientras
que una ruta al temp de alguien esconde el problema.

No bloquea nada del flujo de fabricación (los gerbers no usan modelos 3D). Solo
importa si se quiere un render o el ensamble STEP para el enclosure; en ese caso,
re-importar con `easyeda2kicad` y copiar el `.wrl` a `lib/gamesetup_lcsc.3dshapes/`.

Aparte: `RP2350-Plus_Socket` **no referencia** ningún modelo desde el footprint —
en V1 tampoco lo hacía. Su `RP2350-Plus_Socket.step` existe en
`lib/gamesetup_fp.3dshapes/` y lo consume el pipeline de ensamble STEP, que
trabaja a nivel de placa y no por la propiedad `(model ...)` del footprint. No es
una regresión; queda anotado para que nadie lo "arregle" pensando que falta.

El footprint del LCD tampoco declara modelo 3D: es una pieza que no existe en
ninguna librería. Su altura para el enclosure es el header macho soldado directo
(≈2.5 mm sobre la placa) más el espesor del módulo.

## Qué NO se copió de V1, y por qué

- **`newsetup_lcsc.kicad_sym`** — estaba huérfano: el `sym-lib-table` de V1
  apunta a `newsetup.kicad_sym` (el que genera `gen_sch.py`), no a este. Sus 5
  símbolos son todos de partes que V2 no usa: el tact 4.5×4.5, el OLED
  HS242L01W4S01, el nav SMD SKRHAAE010, el slide MSK12C02 y un MC34064 que no
  está en ninguna placa.
- **Footprints de partes reemplazadas**: `AUDIO-TH_XKB_PJ-320A` (ver V-3),
  `LCD-TH_HS242L01W4S01` (OLED → ST7789), `SW-SMD_SKRHAAE010` (nav SMD → THT),
  `SW-TH_MSK12C02` (slide viejo → SK12D07VG3).
- **`GY-PCM5102_Module`** — V2 va chip-down, no con el módulo.
- **`RotaryEncoder_Alps_EC11E`** — V2 no tiene encoders.
- **`SW-TH_4P-L4.5-W4.5-P3.00-LS5.5`** sí se conservó, aunque V2 use tacts de
  6×6: es el fallback si el 6×6 no llega a tiempo.

## Comando de importación

```
python -m easyeda2kicad --full --lcsc_id=Cxxxxxx
```

Deja los archivos en `~/Documents/Kicad/easyeda2kicad/`. Copiar el `.kicad_mod`
a `lib/gamesetup_lcsc.pretty/`, el modelo 3D a `lib/gamesetup_lcsc.3dshapes/`, y
reapuntar la ruta del modelo a `${KIPRJMOD}/lib/gamesetup_lcsc.3dshapes/`.
