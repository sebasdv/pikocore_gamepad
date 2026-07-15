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
| Select | cicla el modo de parámetro 0–7 (equivale al knob selector) |
| L / R | baja / sube el parámetro activo (Function A); mantener repite |
| Start + L/R | ajusta Function B |
| Up+Down+B+A | reset de FX |
| Up+Right+Y+A | mute / start-stop |
| Down+Left+X+B | lock de clock |

Modos: 0 sample/break · 1 filtro/stretch · 2 gate/prob-gate ·
3 prob-jump/prob-retrig · 4 prob-tunnel/prob-reversa ·
5 secuenciador rec/play · 6 save/load · 7 volumen

## pines

Audio GP18 (parlante/jack del HAT) · LED de beat GP28 · clock in GP22 ·
trigger out GP12 · resto: ver `src/hw_gamepi13.h`.

La UI en el LCD (reemplazo de los 8 LEDs y visualización de knobs) es la
fase 2 del port; los valores ya quedan en memoria (`LED::Val()`).
