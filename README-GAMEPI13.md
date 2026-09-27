# pikocore en RP2350-PiZero + GamePi13

Port de pikocore a la Waveshare RP2350-PiZero con el HAT GamePi13
(LCD 1.3" ST7789, 12 botones, parlante + jack de audio en GP18).

## build

    mkdir -p build-gamepi && cd build-gamepi
    cmake -DPICO_SDK_PATH=../pico-sdk -DPIKO_GAMEPI13=ON ..
    make -j4

Grabar `build-gamepi/pikocore.uf2` (mantener BOOT al conectar USB).
Cargar muestras con la web app (`cd web && npm run dev`).

## controles

| Control | Función |
|---|---|
| Up Down Left Right Y X B A | botones musicales 1–8 de pikocore |
| Select | cicla el modo de parámetro 0–7, y un 9no modo (Browse SD) |
| L / R | baja / sube el parámetro activo (Function A); mantener repite |
| Start (toque simple) | mute / start-stop |
| Start (mantenido) + L/R | ajusta Function B (en modo Volumen, Function B es TEMPO) |
| Up+Down+B+A | reset de FX |
| Up+Right+Y+A | mute / start-stop (alternativa heredada del combo original) |
| Down+Left+X+B | lock de clock |

Modos: 0 sample/break · 1 filtro/stretch · 2 gate/prob-gate ·
3 prob-jump/prob-retrig · 4 prob-tunnel/prob-reversa ·
5 secuenciador rec/play · 6 save/load · 7 volumen/tempo · 8 Browse SD (ver
sección [microSD](#microsd) abajo)

## pantalla

Dashboard 240×240: BPM + fuente de clock, sample (número y nombre), waveform
del sample sonando con playhead y los 8 slices resaltados (reemplaza la
barra de LEDs física del pikocore original), modo del selector con barras
A/B, y puntos de modo. Al presionar Select o L/R aparece un overlay grande
con el modo/parámetro que se desvanece ~1 s después.

## pines

Audio GP18 (parlante/jack del HAT) · LED de beat GP28 · clock in GP22 ·
trigger out GP12 · LCD: SPI1 (CLK GP10, MOSI GP11, CS GP8, DC GP25,
RST GP27, backlight GP7) · resto: ver `src/hw_gamepi13.h`.

Pendiente (Fase 2.1): iconos de estado (mute/seq/lock).

## microSD

Poné archivos `.pikobank` en la raíz de una microSD FAT32 y montala en el
socket integrado del RP2350-PiZero (compartido eléctricamente con el LCD por
SPI1 — protegido por un mutex, ver [GAMEPI13-INTERFACE.md](GAMEPI13-INTERFACE.md)).
Los `.pikobank` se generan con la web app (`cd web && npm run dev`): el botón
"Download bank" arma el banco actual y lo descarga como archivo, listo para
copiar a la tarjeta.

En el instrumento, Select hasta el 9no modo (Browse SD):

- **L** cicla la lista de archivos (una sola dirección; llega a todos igual).
- **Mantener R** ~1 s carga el archivo resaltado — soltar antes cancela sin
  tocar flash. El que ya está sonando aparece resaltado en verde.
- La tarjeta se lee/monta al entrar al modo y se desmonta al salir (Select de
  nuevo). No hay detección de inserción/extracción en caliente: si sacás o
  ponés la tarjeta, hace falta reiniciar el dispositivo.

## más detalle

Ver [GAMEPI13-INTERFACE.md](GAMEPI13-INTERFACE.md) para el detalle de qué hace cada
botón individual, cómo funciona el retrigger, la tabla completa de modos, y notas de
diseño/mejoras futuras.
