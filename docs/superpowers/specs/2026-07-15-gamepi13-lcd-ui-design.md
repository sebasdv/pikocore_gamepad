# UI en el LCD del GamePi13 para pikocore — Diseño (Fase 2)

**Fecha:** 2026-07-15
**Estado:** aprobado por el usuario (modelo híbrido, contenido 1+2+3+5, arquitectura A, layout validado en mockup)
**Prerequisito:** Fase 1 completa y verificada en hardware (rama `port/rp2350-gamepi13`, hasta commit `4f8b5c2`).

## Objetivo

Darle uso a la pantalla ST7789 de 240×240 del GamePi13: reemplazar visualmente los 8 LEDs físicos del pikocore original y hacer visibles el modo/valores de los knobs virtuales que hoy se ajustan a ciegas. La UI es **no-vital**: si el LCD fallara, el instrumento debe seguir sonando idéntico.

## No-objetivos (explícitamente fuera de esta fase)

- Waveform con playhead (candidata a Fase 2.1; el diseño no la bloquea — sería un widget más, probablemente con render DMA).
- Iconos de estado (mute/seq/lock) — misma situación.
- IMU, IR, microSD.
- Cualquier cambio de comportamiento del build original (flag OFF debe quedar byte-idéntico).

## Modelo de interacción (elegido: híbrido)

- **Dashboard base** siempre visible con: BPM+fuente de clock, sample actual (número+nombre), barra de 8 LEDs virtuales, y modo activo con mini-barras A/B + fila de 8 puntos indicando el modo del selector.
- **Overlay temporal** al interactuar: aparece al presionar Select (muestra el modo nuevo) o L/R (muestra parámetro y valor en grande). Se desvanece **1 s (250 ticks a 250 Hz)** después de la última pulsación; al expirar se redibuja la zona de fondo que tapaba. El overlay nunca tapa la barra superior (BPM/sample).

## Layout (coordenadas de framebuffer 240×240, validado en mockup)

| Zona | Área (x, y, w, h) | Contenido |
|---|---|---|
| Barra superior | 0, 0, 240, 28 | BPM (Font20, verde, "♩ 165") + fuente clock ("INT"/"EXT"/"MIDI", gris, Font12) a la izquierda; "NN/MM" (azul, Font16) a la derecha |
| Nombre de sample | 8, 30, 224, 18 | nombre del banco (gris, Font12, truncado a lo que quepa) |
| LEDs virtuales | 10, 60, 220, 24 | 8 cuadrados de 24×24 con 4 px de separación; brillo desde el estado de `LEDArray` (0=apagado → naranja pleno) |
| Bloque de modo | 8, 118, 224, 82 | nombre del modo (rosa, Font16); barra A (224×14, rosa) + etiqueta "A NN%"; barra B (224×14, celeste) + etiqueta "B NN%" |
| Puntos de modo | centrado, 218, –, 8 | 8 puntos de 8 px; el activo en rosa |
| Overlay | 20, 64, 200, 112 | caja con borde rosa: título (p.ej. "FILTRO A"), valor en Font24 grande ("62%"), barra de progreso |

Valores mostrados como porcentaje: `val * 100 / 4095`.

### Nombres de modo (etiquetas en español)

| Modo | Function A (L/R) | Function B (Start+L/R) |
|---|---|---|
| 0 | SAMPLE | BREAK FX |
| 1 | FILTRO | STRETCH |
| 2 | GATE | PROB GATE |
| 3 | PROB SALTO | PROB RETRIG |
| 4 | PROB TUNEL | PROB REVERSA |
| 5 | SEC GRABAR | SEC PLAY |
| 6 | GUARDAR | CARGAR |
| 7 | VOLUMEN | — |

## Arquitectura (elegida: A — core0, dirty-rect)

El render vive en el lazo de control existente de core0 (250 Hz). **Un widget dirty por tick**: se redibuja en el framebuffer con GUI_Paint y se envía solo su ventana por SPI (`LCD_1IN3_DisplayWindows`). Sin redibujos de pantalla completa después del splash. El audio corre por interrupción PWM y no se ve afectado por el busy-wait de SPI (~1–3 ms por widget a 31.25 MHz).

Core1 queda intacto (gestor de samples USB + escrituras a flash) — descartado como render por el riesgo de mezclar SPI del LCD con los stalls de XIP durante escrituras de flash.

### Estructura de módulos (todo compilado solo bajo `PIKO_GAMEPI13`)

```
src/gamepi13/
├── lcd/                  ← vendorizado del demo Gamepi13-RP2040-Demo, casi intacto
│   ├── LCD_1in3.c/h            (driver ST7789 con soporte de ventanas)
│   ├── GUI_Paint.c/h            (primitivas sobre framebuffer)
│   └── font12.c font16.c font20.c font24.c fonts.h
├── dev_shim.c/h          ← sustituye a DEV_Config del demo: pines desde
│                            src/hw_gamepi13.h, spi1 @ 31.25 MHz, backlight
│                            PWM en GP7, SIN i2c y SIN stdio_init_all
└── ui.cpp/h              ← widgets, framebuffer estático (115 200 B), dirty flags
```

### Interfaz pública de `ui.h` (lo único que ve `main.cpp`)

```cpp
void gamepi_ui_init();                       // init LCD + backlight + splash
void gamepi_ui_tick();                       // 1 llamada por tick de 250 Hz
void gamepi_ui_overlay_mode(uint8_t mode);   // Select presionado
void gamepi_ui_overlay_param(uint8_t mode, bool is_b, uint16_t val);  // L/R
```

### Fuentes de datos por widget (todas ya existen en `main.cpp`/Fase 1)

| Widget | Fuente |
|---|---|
| BPM | `bpm_set`; fuente clock: "MIDI" si `clock_input_ittybittymidi`; si no, "EXT" si hubo flanco en CLOCK_PIN en los últimos 2 s (equivale a `is_syncing && do_sync_play`), "INT" en caso contrario |
| Sample | `sample_set`, `piko_audio_sample_count()`, `piko_audio_sample(i).name` |
| LEDs | `LEDArray` — **requiere agregar un getter público** `uint8_t Get(uint8_t i)` que devuelva `vals[i]` (hoy privado); un cambio de ~3 líneas en `doth/ledarray.h` |
| Modo/A/B | `gamepi_selector`, `input_knob[1].Value()`, `input_knob[2].Value()` |
| Overlay | notificaciones push desde los handlers de Select/L/R de Fase 1 + TTL interno |

Los widgets comparan su dato contra lo último dibujado (cache local) y solo se marcan dirty al cambiar; el tick elige el primer dirty y lo procesa.

## Manejo de errores

El ST7789 del GamePi13 es write-only (MISO no conectado): no hay forma de detectar un LCD ausente/fallado. Por diseño, ninguna función de `ui.*` puede bloquear indefinidamente ni afectar el audio; los init tienen los mismos delays fijos del driver Waveshare y nada más. Si la pantalla no muestra nada, el instrumento funciona igual que en Fase 1.

## Pruebas

1. **Builds**: ambas variantes compilan; la variante original (flag OFF) produce exactamente el mismo binario que antes de la fase (verificable por hash del `.uf2` o tamaño de secciones).
2. **Hardware** (checklist del usuario):
   - Splash al arrancar y luego dashboard.
   - LEDs virtuales se mueven con el beat (mismo patrón que los LED físicos del original).
   - BPM mostrado coincide con el configurado; sample NN/MM y nombre correctos tras subir con la web app.
   - Select → overlay de modo; L/R → overlay de parámetro con el valor moviéndose; desaparece ~1 s tras soltar.
   - **Regresión crítica**: el audio suena exactamente igual que en Fase 1 (sin glitches nuevos, botones y knobs virtuales intactos).
3. **Rotación**: pantalla de prueba al primer arranque para validar orientación física (el demo usa `HORIZONTAL` + `ROTATE_270`; confirmar con la serigrafía del GamePi13 y ajustar la constante si sale espejado/rotado).

## Riesgos y decisiones abiertas menores

- **SPI a 31.25 MHz**: el demo usa 10 MHz; el ST7789 tolera ~62 MHz. Si 31.25 diera artefactos, bajar a 15.6 MHz (sigue sobrando: peor caso por widget ~6 ms).
- **Flash**: las 4 fuentes suman ~50 KB de flash — irrelevante con 16 MB.
- **RAM**: framebuffer 115 200 B + ~98 KB actuales ≈ 213 KB de 512 KB — holgado.
