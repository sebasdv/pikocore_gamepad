# Dashboard con bitmaps de Lopaka (modo 0) — Diseño

**Fecha:** 2026-07-19
**Estado:** aprobado por el usuario
**Prerequisito:** Splash con logo de Lopaka completa y verificada en hardware. Rama
`port/rp2350-gamepi13`.
**Riesgo:** medio — primer reemplazo completo del dashboard (antes texto/formas dibujadas
con `Paint_DrawString_EN`/`Paint_DrawRectangle`) por bitmaps, con dos mecanismos nuevos
(blit monocromo, oscurecido de bitmaps a color) sin precedente en este código. Volumen
de datos alto (~19 assets + 20 dígitos), mismo riesgo de transcripción ya visto con la
splash — mitigado exigiendo importación por archivo en el plan.

## Objetivo

Reemplazar el dashboard actual (dibujado con fuentes y formas) por los bitmaps que el
usuario diseñó en Lopaka, para los elementos COMPARTIDOS entre los 9 modos (BPM +
dígitos, fuente de reloj, play/stop, sample idx/count + dígitos, marco de nombre de
archivo, marco de waveform, barras de Function A/B, 9 iconos de modo reemplazando los
8 puntos actuales) y, específicamente para el modo 0, las etiquetas de Function A/B
("SAMPLE"/"BREAK FX") como gráfico en vez de texto.

## No-objetivos

- No cambia la lógica dinámica de la waveform (playhead, resaltado naranja/cian por
  retrigger) — solo su marco (`waveform_frame`) se vuelve un bitmap estático; el
  contenido dinámico se sigue dibujando encima con las mismas líneas de siempre.
- No diseña ahora las etiquetas Function A/B de los modos 1-7 ni el gráfico de reloj
  MIDI — el usuario los va a traer en iteraciones futuras (mismo patrón ya usado con la
  splash: se agregan cuando estén listos). Mientras tanto, esos casos caen a texto
  (`Paint_DrawString_EN`, igual que hoy).
- No toca el overlay temporal de Select/L/R ni las pantallas de Browse SD (modo 8) —
  siguen exactamente como están.
- No agrega variantes atenuadas pre-diseñadas de los iconos de modo — el atenuado del
  icono inactivo se calcula en tiempo de dibujo, no requiere assets adicionales.

## Hallazgos de la investigación (verificados en código, no re-descubrir)

- **3 archivos en `src/gamepi13/`**: `MODE_0.txt` (el frame completo del dashboard +
  las etiquetas de modo 0), `Digits for BPM.txt` (10 dígitos 0-9, anchos variables
  9-11px, alto 15px), `Digits for bank files.txt` (10 dígitos 0-9, anchos variables
  7-9px, alto 10-12px).
- **Formato de exportación Lopaka** (target TFT_eSPI/Lovyan): la mayoría de los assets
  son arrays `uint16_t` RGB565 usados con `tft.pushImage(x,y,w,h,data)` — mapean
  directo a `Paint_DrawImage()`, ya usado para la splash, con el mismo cast
  `(const unsigned char*)` sin conversión de bytes (mismo razonamiento de endianness ya
  validado ahí).
- **Excepción**: `image_play_bits`/`image_stop_bits` son arrays `unsigned char` (1 bit
  por pixel empaquetado, MSB primero) usados con `tft.drawBitmap(x,y,bits,w,h,color)`
  — `GUI_Paint` no tiene una función equivalente, hace falta escribir una nueva.
- **`PROGMEM` debe quitarse** igual que en la splash — no existe en este target, y
  `static const` ya vive en flash.
- **Todos los assets se importan vía archivo + `sed`/`cat`, nunca retipeados a mano** —
  la splash ya demostró que retipear un array grande (miles de valores repetitivos)
  pierde entradas de forma silenciosa. El usuario ya sabe guardar el export de Lopaka
  como archivo antes de pasarlo.
- **Estructura de `MODE_0.txt`** (posiciones reales en el lienzo de 240×240, ya
  confirmadas contra un mockup reconstruido y validadas por el usuario):
  - `play`/`stop` (mono, 12×12): `(212,7)` y `(226,7)`.
  - BPM: 3 slots de dígito en `(2,6)`, `(14,6)`, `(26,6)` en el mockup (posiciones de
    ejemplo con el mismo dígito repetido — los dígitos reales tienen ancho variable,
    ver Mecanismo).
  - `Int_clock` `(44,6,38,14)` / `Ext_clock` `(100,6,40,14)`, con `BPM_Slash`
    `(84,3,14,20)` entre el BPM y la fuente de reloj.
  - Sample idx/count: 4 slots de dígito en `(194,32)`, `(203,32)`, `(222,32)`,
    `(231,32)` + `file_bank_slash` `(212,31,7,15)`, formato `NN/NN` — reemplaza el
    `"NN/MM"` de texto que ya existe hoy (mismo dato: `sample_idx+1`/`sample_count`).
  - `filename_sample_frame` `(0,29,191,20)`.
  - `waveform_frame` `(0,54,240,48)` — estático; el contenido dinámico no cambia.
  - `SAMPLE_WORD` `(1,107,88,20)` — etiqueta Function A de modo 0.
  - `SAMPLE_BAR` `(0,132,240,20)` — barra Function A.
  - `BREAK_FX_WORD` `(0,157,119,20)` — etiqueta Function B de modo 0.
  - `BREAK_FX_BAR` `(0,182,240,20)` — barra Function B.
  - `M_0`..`M_7` (16×21 c/u, `x = 27 + 18*i`, `y=207`) + `M_SD` `(171,207,31,21)` — 9
    iconos de modo (todos `uint16_t`/RGB565), reemplazan los 8 puntos actuales.

## Mecanismo

### Dígitos con ancho real (BPM y sample idx/count)

Una tabla por set de 10 dígitos:

```cpp
struct DigitGlyph { const uint16_t* pixels; uint8_t w, h; };
static const DigitGlyph kBpmDigits[10] = { {img_bpm_0, 10, 15}, ... };
static const DigitGlyph kBankDigits[10] = { {img_bank_0, 7, 12}, ... };
```

Una función `draw_digit_string(x, y, const char* text, const DigitGlyph* set, uint8_t slash_w, const uint16_t* slash_pixels, bool right_align)` que:
- Si `right_align`, primero suma los anchos reales de cada carácter (incluyendo `/`)
  para calcular el punto de inicio, de forma que el borde DERECHO del número quede
  fijo aunque cambie la cantidad de dígitos.
- Recorre cada carácter, blitea con `Paint_DrawImage` (dígitos) o el asset fijo del
  slash, y avanza el cursor por el ancho REAL de ese carácter — mismo efecto visual
  "pegado" que el diseño de Lopaka, sin grilla de ancho fijo.

BPM (2-3 dígitos) usa `right_align=true` con el borde DERECHO del número anclado en
`x≈40` (justo antes de donde arranca `Int_clock`/`Ext_clock` en `x=44`) — al pasar de 2
a 3 dígitos, el número crece hacia la izquierda en vez de invadir la zona del reloj.
Sample idx/count usa el mismo mecanismo para el formato `"NN/NN"`.

### Play/stop (mono, un solo color)

Nueva función:

```cpp
void Paint_DrawMonoBitmap(uint16_t x, uint16_t y, const unsigned char *bits,
                           uint16_t w, uint16_t h, uint16_t color);
```

Recorre los bits empaquetados (MSB primero, filas alineadas a byte — mismo formato que
ya usa `image_play_bits`/`image_stop_bits`), y llama a `Paint_SetPixel` solo donde el
bit está en 1, con el `color` dado. Los dos íconos se dibujan SIEMPRE; el activo usa el
color normal (blanco), el inactivo un color atenuado (`COL_GRAY`, ya existente en la
paleta del dashboard).

### Iconos de modo (color, atenuado calculado)

Nueva función de oscurecido RGB565:

```cpp
uint16_t dim_rgb565(uint16_t color, uint8_t factor);  // factor 0-255, 255=sin cambio
```

Reduce cada canal (R:5 bits, G:6 bits, B:5 bits) proporcionalmente al factor dado. Una
variante del blit existente aplica `dim_rgb565` pixel por pixel al dibujar un icono
inactivo, saltando el color de fondo (`0x0000`, ya negro, no necesita oscurecerse más).
Los 9 iconos (`M_0`..`M_7`, `M_SD`) se dibujan siempre; el que corresponde al modo
activo se dibuja tal cual, los otros 8 pasan por `dim_rgb565`.

### Etiquetas Function A/B (bitmap solo modo 0, texto fallback en el resto)

Se agrega una tabla paralela a las de texto ya existentes (`kModeA`/`kModeB`), con
punteros opcionales a bitmap por modo (`nullptr` = no hay gráfico todavía, usar texto):

```cpp
struct ModeLabelBitmap { const uint16_t *pixels; uint8_t w, h; };
static const ModeLabelBitmap *kModeABitmap[8] = { &kSampleWord, nullptr, nullptr, ... };
static const ModeLabelBitmap *kModeBBitmap[8] = { &kBreakFxWord, nullptr, nullptr, ... };
```

Al dibujar la etiqueta de Function A/B, si la entrada correspondiente al modo activo no
es `nullptr`, se blitea el bitmap; si es `nullptr`, se usa `Paint_DrawString_EN` con
`kModeA[mode]`/`kModeB[mode]` exactamente como hoy. El reloj en modo MIDI sigue el
mismo patrón: sin gráfico propio todavía, cae a texto (`Font12`, `"MIDI"`).

## Arquitectura

Nuevo archivo `src/gamepi13/ui_bitmaps.h` con todos los arrays de píxeles vendorizados
(sin `PROGMEM`), las tablas de dígitos y etiquetas, y los dos helpers nuevos
(`Paint_DrawMonoBitmap`, `dim_rgb565` + su variante de blit). `ui.cpp` se modifica para
que `gamepi_ui_tick()` dibuje estos bitmaps en cada zona en vez de texto/formas,
manteniendo intacto el sistema ya existente de `kRect[]`/`dirty[]`/throttle a ~25Hz —
cambia SOLO el contenido de cada callback de dibujo (qué se pinta), no el mecanismo de
cuándo se pinta.

## Manejo de errores

No aplica — no hay entradas externas ni estados inválidos nuevos; los datos de bitmap
son estáticos y confiables una vez importados correctamente (verificados por conteo de
píxeles antes de compilar, mismo método ya usado con la splash).

## Pruebas

1. **Build**: ambas variantes compilan; el build original (flag OFF) sin cambios — todo
   vive en `ui.cpp`/`ui_bitmaps.h`, ya exclusivos de GamePi13.
2. **Hardware — modo 0**: BPM, fuente de reloj (INT/EXT), play/stop, sample idx/count,
   nombre de archivo, waveform con marco nuevo (contenido dinámico sin cambios), barras
   Function A/B, "SAMPLE"/"BREAK FX" como gráfico, 9 iconos de modo con el activo
   resaltado y los demás atenuados — todo coincide visualmente con el diseño de Lopaka.
3. **Hardware — cambio de modo** (Select): el icono de modo activo cambia
   correctamente; modos 1-7 muestran su etiqueta de Function A/B en texto (fallback);
   modo 8 (Browse SD) muestra su icono `M_SD` activo.
4. **Hardware — reloj en MIDI**: muestra texto `"MIDI"` (fallback), sin romper el
   layout de los elementos vecinos.
5. **Hardware — BPM de 2 a 3 dígitos** (ej. 99→100): los dígitos no colisionan con el
   reloj, siguen alineados a la derecha.
6. **Regresión**: overlay temporal de Select/L/R, pantallas de Browse SD, resaltado
   cian de retrigger en la waveform — todo sin cambios.

## Riesgos conocidos

- **Volumen de datos**: ~19 assets + 20 dígitos a importar — mismo riesgo de
  transcripción que la splash, mitigado exigiendo import por archivo+`sed` en el plan
  de implementación, nunca retipeo manual.
- **Primera vez que se oscurece un bitmap a color en tiempo real** (`dim_rgb565`) —
  mecanismo nuevo, sin precedente en este código; se verifica visualmente en hardware
  (Prueba 2).
- **Diseño parcial aceptado**: 8 modos + reloj MIDI sin gráfico propio todavía — el
  fallback a texto ya está decidido y no bloquea esta fase; se suman cuando el usuario
  los diseñe en Lopaka.
