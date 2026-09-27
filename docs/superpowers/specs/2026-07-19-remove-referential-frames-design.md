# Quitar frames referenciales del dashboard — Diseño

**Fecha:** 2026-07-19
**Estado:** aprobado por el usuario
**Prerequisito:** Dashboard con bitmaps de Lopaka (modo 0) completo y verificado en
hardware. Rama `port/rp2350-gamepi13`.
**Riesgo:** bajo — elimina código y datos, no agrega nada nuevo.

## Objetivo

`filename_sample_frame` y `waveform_frame` (dibujados en `draw_name()`/`draw_wave()`,
`src/gamepi13/ui.cpp`) son guías de layout de Lopaka, no assets pensados para
dibujarse en tiempo real — marcan la cavidad donde va el contenido dinámico (nombre
del sample, forma de onda), no un marco decorativo real. Se confirma revisando los 8
archivos de modo (`MODE_0.txt`..`MODE_7.txt`): ambos assets aparecen idénticos
(mismas dimensiones y posición) en los 8, consistente con ser una guía fija del
lienzo, no contenido que varíe por modo.

## No-objetivos

- No se agrega ningún marco decorativo nuevo en su lugar.
- No cambia nada del contenido dinámico de esas dos zonas (nombre de sample + índice,
  forma de onda + playhead + resaltado).

## Mecanismo

- Se quitan las dos llamadas a `Paint_DrawImage` que dibujan estos assets en
  `draw_name()` y `draw_wave()`.
- Se borran los arrays `kFilenameFrame` y `kWaveformFrame` de
  `src/gamepi13/ui_bitmaps.h` por completo (no se guardan "por si acaso") — son ~15KB
  de datos que ya no se usan en ningún lado del código.

## Arquitectura

Sin cambios de arquitectura — es una resta de dos líneas de dibujo y dos arrays de
datos, dentro de los mismos archivos ya existentes.

## Manejo de errores

No aplica.

## Pruebas

1. Build `build-gamepi`: sin errores (nada más referencia estos dos arrays).
2. Hardware: la zona de nombre de sample y la zona de waveform se ven exactamente
   igual que antes en su contenido dinámico (nombre, índice, forma de onda, playhead,
   resaltado de retrigger) — solo desaparece el marco decorativo que las rodeaba.

## Riesgos conocidos

Ninguno relevante — cambio puramente sustractivo.
