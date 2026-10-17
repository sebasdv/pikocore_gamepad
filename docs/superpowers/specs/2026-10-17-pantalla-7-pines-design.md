# pikocore_gamepad — pantalla: modulo IPS 1.3" de 7 pines en lugar del panel de 24 pines

Fecha: 2026-10-17. Rama: `hw/pantalla-7pines`, cortada de `hw/modulo-micro-midi` (PR #3).
Estado (2026-10-17): implementado y ruteado en la rama (commits 33c623f..57ebe7d, puertas en
el commit de docs). Puertas: 218 tests OK; ERC 0/0; DRC 0 errores / 0 sin conectar / 0 paridad
(15 avisos); G-5/G-4/G-2/placement OK; G-0 rojo solo por `LCD7_PIN_ROW_TO_EDGE` y
`LCD7_PIN_DRILL` (por medir con el modulo en mano), asi que el paquete sale `NO-FABRICABLE`.

## Por que

El panel desnudo DM-TFT13-377 de 24 pines deja `LCD_FPC_PIN_ORDER` (G-0, V-8) sin
cerrar: hay que saber de que cara del flex salen los contactos y el usuario no
tiene el panel. El usuario **tiene en casa** el modulo IPS 1.3" 240x240 ST7789 de 7
pines (EC-Buying, AliExpress 32880670572), el mismo tipo que usaba la placa antes
del commit 4d66184. Con ese modulo la unica incertidumbre es una medicion con calibre.

## Que cambia

| Area | Hoy (panel de 24 pines) | Con el modulo de 7 pines |
|---|---|---|
| Conexion | FPC 0.5 mm 24P en J4 (XUNPU C2856831, SMD, frente) | 7 agujeros pasantes a 2.54 mm; los pines del modulo se sueldan a la placa |
| Backlight | R21 27R + Q1 2N7002 + R22 100k + C30/C31 | los lleva el modulo; `LCD_BLK` va directo al pin BLK, como en la placa vieja |
| Pines | GP2 SCK, GP3 MOSI, GP5 DC, GP6 RES, GP7 BLK, GP26 TE | iguales salvo GP26: el modulo no tiene TE, queda libre |
| CS / IM | CS a GND, IM=1 en la placa | CS a GND ya esta en el modulo |
| G-0 | `LCD_FPC_PIN_ORDER` rojo | desaparece; quedan dos parametros de medicion del modulo |

Nets del modulo (pin 1 a 7): GND, 3V3, `LCD_SCK`, `LCD_MOSI`, `LCD_RES`, `LCD_DC`, `LCD_BLK`.

## Geometria (dibujo del fabricante, confirmado por el usuario el 2026-10-17)

El dibujo del modulo (27.78 x 39.22; pin 1 a 6.27 del borde izquierdo; paso 2.54;
agujeros de 2 mm a 2.5 mm de los bordes; area activa 23.40 con 5.00 + 1.33 de borde
superior a ventana) coincide con la huella vieja `LCD_ST7789_240x240_7P.kicad_mod`
(commit 4d66184~1). Origen = pin 1, X a lo largo de la fila de pines, Y hacia el cuerpo:

- Placa 27.78 x 39.22 mm: x -6.27..21.51, y -1.27..37.95.
- Pines en y = 0, x = 0, 2.54 ... 15.24; pad 1.7 mm, taladro 1.0 mm.
- Area activa 23.4 mm cuadrada: x -4.08..19.32, y 5.06..28.46, centro (7.62, 16.76).
- 4 agujeros de 2.0 mm en (-3.77, 1.23), (19.01, 1.23), (-3.77, 35.45), (19.01, 35.45).
  **No se taladran** en la placa: el modulo se sostiene por sus pines.
- Sin dato en el dibujo: la distancia del eje de pines al borde (1.27 viene de la huella
  vieja) y el diametro real de los pines: quedan `verified=False`.

## Colocacion

Los pines salen por el dorso, donde va el modulo RP2350-Plus (x 38.9..61.1, y 7.5..58.5):
ahi no puede haber patas pasantes. Por eso la fila de pines va **arriba**, entre los
dos jacks MIDI, antes del borde superior del RP2350:

- Centro del area activa en (50.0, 22.5): pin 1 en (42.38, 5.74), pin 7 en (57.62, 5.74).
- Los pads llegan a y = 6.59; el RP2350 empieza en y = 7.5: 0.9 mm de margen.
- El cuerpo del modulo cubre x 36.11..63.89, y 4.47..43.69 en el frente. Las bandas de
  los jacks (x < 37.6 y x > 62.3) estan en el dorso y no chocan.
- El centro baja de 24.0 a 22.5 respecto del diseno Micro; D-pad y rombo no se mueven.
- Se libera el frente bajo el modulo (donde estaba J4, y 52.4).

## Pipeline

`netlist.py` (J4 pasa a 7 pines; fuera LCD1, R21, Q1, R22, C30, C31 y el simbolo FPC),
`gen_sch.py` (hoja 02 y su nota), `gen_fp.py` (generador del modulo de 7 pines en lugar
del panel), `params.py` (fuera `PANEL_*` y `LCD_FPC_PIN_ORDER`; entran las cotas del
modulo como no verificadas), `pinmap.py` + `config.h` (GP26 libre, sin `PIN_LCD_TE`),
`placements.py`, tests y checks; luego el ciclo de ruteo y las puertas.

## Pendiente de medir con el modulo en mano

1. Distancia del eje de los pines al borde del lado de los pines (1.27 esperado).
2. Diametro de los pines del modulo (taladro de 1.0 mm supuesto).

Hasta entonces esos dos parametros quedan `verified=False` y G-0 sigue rojo; medidos,
pasan a verificados y el paquete pasa a `FABRICABLE` si no queda otro rojo.

Tampoco verificado:

- Un 1 uF opcional en J4 pin 2 (3V3), a agregar la proxima vez que se regenere la placa.
- La polaridad y el estado de pull de BLK en el modulo: desconocidos hasta medirlo (el
  firmware asume activo en alto).

## Fuera de alcance

Firmware del driver (ya es ST7789 240x240), la caja, y volver al panel de 24 pines.
