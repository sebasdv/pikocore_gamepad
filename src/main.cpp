// c++ include
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <cmath>

// pico files
#include "hardware/adc.h"  // adc_read
#include "hardware/clocks.h"
#include "hardware/flash.h"  // flash memory
#include "hardware/irq.h"    // interrupts
#include "hardware/pwm.h"    // pwm
#include "hardware/sync.h"   // wait for interrupt
#include "pico/binary_info.h"
#include "pico/stdlib.h"  // stdlib
#include "pico/multicore.h"
#include "tusb.h"

#include "PikoAudioBank.h"
#include "PikoSampleManager.h"
// pikocore files
#include "doth/button.h"
#include "doth/delay.h"
#include "doth/easing.h"
#include "doth/filter.h"
#include "doth/knob.h"
#include "doth/virtualknob.h"
#include "doth/led.h"
#include "doth/ledarray.h"
#include "doth/midi_out.h"
#include "doth/onewiremidi.h"
#include "doth/runningavg.h"
#include "doth/sequencer.h"
#include "doth/trigger_out.h"

// constants
#define CLOCK_RATE 248000
#define SAMPLE_RATE 24000
#define BPM_SAMPLED 165
#define SAMPLES_PER_BEAT 4364
#define NUM_RETRIGS 19
#define raw_val piko_raw_val
#define raw_len piko_raw_len
#define raw_beats piko_raw_beats
#define NUM_BUTTONS 8
#define NUM_KNOBS 3
#define NUM_LEDS 8
#define DISTORTION_MAX 30
#define VOLUME_REDUCE_MAX 30
#define HEAD_SHIFT 10  // crossfade time in samples (2^HEAD_SHIFT)
#if PIKO_GAMEPI13
#include "hw_gamepi13.h"
#define AUDIO_PIN GAMEPI_AUDIO_PIN
#define LED_PIN GAMEPI_LED_PIN
#define CLOCK_PIN GAMEPI_CLOCK_PIN
#define TRIGO_PIN GAMEPI_TRIGO_PIN
// GamePi13 has no WS2812 strip; GP23 (original strip pin) is the L button.
#undef WS2812_ENABLED
#define WS2812_ENABLED 0
#include "gamepi13/ui.h"
#include "PikoSampleManager.h"
#include "gamepi13/lcd/DEV_Config.h"  // gamepi_spi1_mutex_init()
#else
#define AUDIO_PIN 20   // audio out
#ifdef PICO_DEFAULT_LED_PIN
#define LED_PIN PICO_DEFAULT_LED_PIN
#endif
#define CLOCK_PIN 22  // clock in pin
#define TRIGO_PIN 21  // trigger out pin
#endif
#define MAIN_LOOP_HZ 4
#define MAIN_LOOP_DELAY 50

#if WS2812_ENABLED == 1
#include "doth/WS2812.hpp"
#endif
/*
 * GLOBAL VARIABLES
 */

// flash
// https://github.com/raspberrypi/pico-examples/blob/master/flash/program/flash_program.c
// https://kevinboone.me/picoflash.html
#define SAVE_VOLUME 0  // needs two bytes
#define SAVE_BPM 2     // needs two bytes
#define SAVE_FILTER 4  // needs one byte
#define SAVE_SAMPLE 5  // needs one byte
#define SAVE_GATE 6    // needs two bytes
#define SAVE_PROB_DIRECTION 8
#define SAVE_PROB_RETRIG 9
#define SAVE_PROB_JUMP 10
#define SAVE_PROB_GATE 11
#define SAVE_PROB_TUNNEL 12
#define SAVE_CLOCK_INPUT_MODE 13
// GamePi13: posición de los knobs virtuales de Function A/B por modo.
// 8 modos x 2 knobs x 2 bytes = 32 bytes, ocupa 14..45. Es zona libre: el
// secuenciador se queda con 98/99 y 100..227 (ver sequencer.h), y los
// marcadores de validez viven en FLASH_PAGE_SIZE-1..-4.
#define SAVE_KNOB_BY_MODE 14
// Un save anterior a esta versión tiene ceros en 14..45, indistinguible de
// "todos los knobs guardados en 0". Este byte mágico dice si el bloque es
// válido; si no lo es, se conservan los valores por defecto.
#define SAVE_KNOB_MAGIC 46
#define SAVE_KNOB_MAGIC_VALUE 0xA5
// El filtro (SAVE_FILTER, byte 4) tenía slot reservado desde el pikocore
// original pero nunca se escribía, y la línea que lo restauraba estaba
// comentada -- o sea, el LPF no sobrevivía al apagado. Ahora sí se persiste,
// con su PROPIO byte mágico (no reusa el de los knobs) porque un save escrito
// antes de este cambio tiene 0 en SAVE_FILTER, y restaurar filter_fc=0 dejaría
// el filtro cerrado del todo -- audio apagado al bootear.
#define SAVE_FILTER_MAGIC 47
#define SAVE_FILTER_MAGIC_VALUE 0x5A
#define CLOCK_INPUT_CLOCK 0
#define CLOCK_INPUT_MIDI 1
#define MIDI_NOTES_AVAILABLE_TOTAL 28
static constexpr uint32_t kKnobMax = 4095u;
static constexpr uint32_t kStretchQ8One = 256u;
static constexpr uint32_t kStretchQ8Bypass =
    (11u * kStretchQ8One + 5u) / 10u;
static constexpr uint32_t kStretchQ8Max = 10u * kStretchQ8One;
static constexpr uint32_t kGrainLengthSamples = 2048u;
static constexpr uint32_t kGrainHopSamples = 1024u;
static constexpr uint32_t kGrainHopShift = 10u;
static constexpr uint64_t kTimestretchPhaseIncQ32 = 1ull << 32u;
uint8_t midi_notes_available[MIDI_NOTES_AVAILABLE_TOTAL] = {
    36, 38, 40, 41, 43, 45, 47, 48, 50, 52, 53, 55, 57, 59,
    60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83};
uint8_t midi_notes_set[8] = {36, 38, 40, 41, 43, 45, 47, 48};

const uint8_t *flash_target_contents =
    (const uint8_t *)(XIP_BASE + PIKO_SETTINGS_FLASH_OFFSET);

// inputs
Button input_button[NUM_BUTTONS];
#if PIKO_GAMEPI13
VirtualKnob input_knob[NUM_KNOBS];
Button btn_select, btn_start, btn_l, btn_r;
uint8_t gamepi_selector = 0;

// Persistencia por modo de los knobs virtuales de Function A/B.
// En el pikocore original los knobs son potenciómetros FÍSICOS: su posición ES
// el valor, y al cambiar de modo el pot se queda donde está (el Reset() de allá
// implementa "pickup" para no aplicar de golpe esa posición vieja al parámetro
// del modo nuevo). Al portarlo a knobs virtuales quedó UN solo valor por knob
// compartido entre los 8 modos, así que al cambiar de modo la barra mostraba el
// valor del modo ANTERIOR y el siguiente toque de L/R saltaba desde ahí.
// Ojo: los parámetros en sí nunca se corrompían -- al cambiar de modo Changed()
// queda en false para los knobs 1/2, así que no se re-aplican. Lo único que
// faltaba era que el knob recordara su posición por modo, que es esto.
// Arrancan en 2048 (el mismo mid-scale de VirtualKnob::Init) porque al bootear
// no hay forma de saber a qué posición de knob corresponde cada parámetro
// cargado de flash: haría falta la función inversa de cada mapeo. Hasta el
// primer ajuste, la barra de un modo no visitado muestra ese medio.
// Excepción del modo 1 Function B (timestretch): arranca en 0, no en el medio.
// stretch_q8 arranca en kStretchQ8One (= sin stretch), y stretch_from_knob_q8(0)
// da exactamente eso, así que knob y parámetro quedan consistentes desde el
// boot. Con 2048 el knob mentía (barra a media asta sin stretch aplicado) y, al
// restaurarlo en la carga, habría metido stretch donde no había.
static uint16_t gamepi_knob_by_mode[8][2] = {
    {2048, 2048}, {2048, 0},    {2048, 2048}, {2048, 2048},
    {2048, 2048}, {2048, 2048}, {2048, 2048}, {2048, 2048}};

// El modo 8 (Browse SD) no tiene Function A/B, así que se ignora en ambos
// sentidos: se sale de él con los knobs del modo destino intactos.
static void gamepi_store_mode_knobs(uint8_t mode) {
  if (mode >= 8) return;
  gamepi_knob_by_mode[mode][0] = input_knob[1].Value();
  gamepi_knob_by_mode[mode][1] = input_knob[2].Value();
}
static void gamepi_restore_mode_knobs(uint8_t mode) {
  if (mode >= 8) return;
  input_knob[1].SetQuiet(gamepi_knob_by_mode[mode][0]);
  input_knob[2].SetQuiet(gamepi_knob_by_mode[mode][1]);
}
// Guarda la posición de los knobs del modo que se deja y restaura la del que se
// entra.
static void gamepi_switch_mode_knobs(uint8_t from, uint8_t to) {
  if (from == to) return;
  gamepi_store_mode_knobs(from);
  gamepi_restore_mode_knobs(to);
}

// Modo 6 (Save/Load state): instante en que la escritura/lectura de flash
// REALMENTE ocurrió. El ícono del dashboard se enciende durante
// GAMEPI_STATE_FLASH_US a partir de ahí. Se usa el momento de concreción y no
// el de "armado" porque el guardado tiene un debounce de por medio: armar no
// es haber grabado. El 0 inicial se trata como "nunca pasó" para que el ícono
// no se encienda solo al bootear.
uint64_t gamepi_state_saved_us = 0;
uint64_t gamepi_state_loaded_us = 0;
#define GAMEPI_STATE_FLASH_US 1500000ull

// Indicador de los íconos del modo 6: true = lo que está en memoria coincide
// con lo que hay en flash. Se enciende al guardar y al cargar (ahí memoria y
// flash coinciden por definición) y se apaga en cuanto se toca un parámetro.
//
// Es un ESTADO PERMANENTE y no un flash temporal a propósito. La primera
// versión encendía el ícono 1,5 s tras guardar, y reproduciendo no se veía: el
// dashboard dibuja UN widget por ventana de flush, por índice, y si el
// redibujo de esa zona se pierde en esa ventana el aviso se pierde con él
// (confirmado en hardware: reproduciendo tampoco volvía a 0 la barra, o sea la
// zona entera quedaba sin redibujar). Al ser un estado persistente, cualquier
// redibujo posterior muestra el valor correcto -- no hay instante que perder.
// Además informa algo más útil: si te falta guardar.
bool gamepi_state_in_sync = false;

// El modo 6 no controla un "parámetro": sus dos barras son un gesto MOMENTÁNEO
// (llenar la barra = disparar la acción). Se vacían después de cada acción por
// dos motivos:
//  1. El latch del original (has_saved / has_loaded) solo se re-arma cuando el
//     valor vuelve a bajar del umbral. Con un pot físico eso pasaba solo al
//     mover la mano; con knob virtual la barra quedaba clavada arriba y había
//     que bajarla a mano con L para poder volver a guardar.
//  2. Al cargar un estado se restauraría la barra en el tope (donde quedó al
//     guardar), mostrando el modo 6 como si ya se hubiera disparado.
// Si el usuario ya cambió de modo (el guardado tiene debounce), se limpia solo
// la entrada de la tabla: el knob vivo ya pertenece a otro modo.
// "Un gesto = una acción" en el modo 6. Se arma al concretarse un save/load y
// se libera al soltar L/R. Mientras está armado, el auto-repeat NO mueve la
// barra.
//
// Sin esto, mantener R apretado encadenaba escrituras: la barra se vacía al
// guardar, el repeat la vuelve a llenar en ~100ms, cruza el umbral otra vez y
// RE-DISPARA el guardado, en loop mientras no sueltes. Confirmado como causa de
// tres síntomas que parecían distintos -- la barra que nunca se veía en 0, el
// guardado que "tardaba" (guardaba varias veces seguidas) y el stutter (cada
// escritura son ~100ms con interrupciones deshabilitadas). Y encima desgasta la
// flash, que tiene ciclos de borrado finitos.
//
// Se notaba mucho más con el audio sonando porque ahí el debounce del guardado
// avanza más lento (la ISR de audio se lleva el CPU), así que es casi seguro
// que el botón siga apretado cuando la escritura por fin ocurre.
bool gamepi_state_bar_latched = false;

static void gamepi_clear_state_bars() {
  gamepi_knob_by_mode[6][0] = 0;
  gamepi_knob_by_mode[6][1] = 0;
  if (gamepi_selector == 6) {
    input_knob[1].SetQuiet(0);
    input_knob[2].SetQuiet(0);
  }
  gamepi_state_bar_latched = true;
}
// Real-elapsed-time gating for L/R auto-repeat (Function A/B). See
// GAMEPI_REPEAT_US's comment in hw_gamepi13.h for why this isn't tick-based
// anymore.
uint64_t gamepi_next_repeat_l_us = 0;
uint64_t gamepi_next_repeat_r_us = 0;
// Hold-start timestamps for the tempo (mode 7 Function B) direct bpm_set
// adjustment -- 0 means "not currently holding this button for tempo".
// Separate from gamepi_next_repeat_*_us (which only gates "when to apply the
// next step", not "how long has this hold lasted", needed here to pick the
// 1/5/20 BPM tier).
uint64_t gamepi_tempo_hold_l_us = 0;
uint64_t gamepi_tempo_hold_r_us = 0;
// Cuenta pasos dados durante el hold actual de L/R, para cualquier parámetro
// (se resetea a 0 al soltar) -- ver GAMEPI_FIRST_REPEAT_US en hw_gamepi13.h
// para por qué el paso #2 espera más que los siguientes. Satura en 2: sólo
// interesa distinguir "recién di el primero" del resto, y así no puede
// desbordar en un hold largo.
uint8_t gamepi_repeat_count_l = 0;
uint8_t gamepi_repeat_count_r = 0;
bool gamepi_start_used_as_modifier = false;
// Mirrors gamepi_start_used_as_modifier: Select's own tap-vs-hold-modifier
// distinction (see the Select handler in main()) for the new "hold Select +
// musical button = jump directly to that mode" gesture.
bool gamepi_select_used_as_modifier = false;

// Cantidad de modos que cicla Select. Con PIKO_GAMEPI13_SD=0 (por defecto) el
// modo 8 (Browse SD) queda APARCADO: el selector cicla 0-7 y nunca llega al 8,
// asi que toda la maquinaria de SD de abajo queda inalcanzable en runtime (cero
// actividad en el bus spi1 que comparte con el LCD, que es de donde salieron
// los tres bugs encadenados de SD). El codigo sigue compilando intacto: alcanza
// con -DPIKO_GAMEPI13_SD=ON para reactivarlo. Cargar samples por USB no se ve
// afectado. Ver el comentario en CMakeLists.txt.
#if PIKO_GAMEPI13_SD
#define GAMEPI_MODE_COUNT 9
#else
#define GAMEPI_MODE_COUNT 8
#endif

// Modo 8 (Browse SD) state machine.
enum GamepiSdState {
  GAMEPI_SD_IDLE,      // not in mode 8, or entered but nothing requested yet
  GAMEPI_SD_LISTING,   // waiting for gamepi_sd_list_done
  GAMEPI_SD_BROWSE,    // list ready, user navigating with L/R
  GAMEPI_SD_LOADING,   // waiting for gamepi_sd_load_done
  GAMEPI_SD_RESULT,    // showing success/fail briefly
};
GamepiSdState gamepi_sd_state = GAMEPI_SD_IDLE;
uint32_t gamepi_sd_index = 0;
// 0 = not currently holding R to confirm a load; otherwise the time_us_64()
// timestamp when the hold began. Dedicated to mode 8 -- no longer shares
// storage with gamepi_next_repeat_r_us (Function A/B's own repeat timer),
// which was a deliberate but fragile Phase-3 shortcut relying on the two
// use sites never running in the same tick.
uint64_t gamepi_sd_hold_start_us = 0;
#define GAMEPI_SD_HOLD_CONFIRM_US 1000000  // ~1 s real hold to confirm a load
uint64_t gamepi_sd_result_deadline_us = 0;
// Deliberately longer than the old (mis-timed) "brief pause" intent -- 1.5 s
// is long enough to actually read "Listo: <filename>" or "Error", which the
// original ~0.4 s nominal intent (itself under a broken time base) wasn't
// really designed to guarantee either.
#define GAMEPI_SD_RESULT_US 1500000  // ~1.5 s
char gamepi_active_bank_name[24] = "";  // "" until a bank is loaded from SD this session
// Qué pantalla del modo 8 falta (re)dibujar -- ver el bloque junto a
// gamepi_ui_tick() más abajo, que reintenta cada tick hasta que la llamada
// correspondiente devuelva true (flush_allowed() puede denegar la primera
// vez sin que eso signifique que la pantalla nunca deba mostrarse).
// Independiente de GamepiSdState (arriba): ese enum maneja en qué paso de
// la máquina de estados estamos, este maneja si ya se logró dibujar la
// pantalla correspondiente a ese paso.
enum GamepiSdRedrawKind {
  GAMEPI_SD_REDRAW_NONE,
  GAMEPI_SD_REDRAW_LISTING,
  GAMEPI_SD_REDRAW_BROWSE,
  GAMEPI_SD_REDRAW_LOADING,
  GAMEPI_SD_REDRAW_RESULT,
  GAMEPI_SD_REDRAW_ERROR,
};
GamepiSdRedrawKind gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_NONE;
char gamepi_sd_redraw_error_msg[32] = "";
#else
Knob input_knob[NUM_KNOBS];
#endif

// outputs
LEDArray ledarray;

TriggerOut output_trigger;

// audio tracking
uint8_t audio_now = 0;
uint16_t audio_clk = 0;
uint16_t audio_clk_thresh = 48;
bool do_mute = false;
uint8_t do_mute_debounce = 0;

// midi out
MidiOut *midiout;

// sample tracking
uint16_t sample = 0;
uint16_t sample_beats = 8;
uint16_t sample_source_bpm = BPM_SAMPLED;
uint32_t sample_frames_per_slice = SAMPLES_PER_BEAT;
uint16_t sample_change = 0;
uint16_t sample_add = 0;
uint16_t sample_set = 0;
uint32_t phase_sample[] = {0, 0};
uint32_t phase_retrig = 0;
bool phase_head = 0;
uint32_t phase_xfade = 0;

// beat tracking
uint16_t select_beat = 0;
uint16_t select_beat_freeze = 0;
bool direction[] = {1, 1};  // 0 = reverse, 1 = forward
bool base_direction = 1;    // 0 = reverse, 1 == forward
uint8_t volume_mod = 0;

struct TimestretchGrain {
  uint64_t start_phase_q32;
  uint64_t phase_inc_q32;
  uint16_t age;
};

// volume/distortion/filter/bitcrush/stretch
uint8_t distortion = 0;
uint8_t volume_reduce = 0;
uint8_t filter_fc = LPF_MAX + 10;
uint8_t hpf_fc = 0;
uint8_t filter_q = 0;
uint8_t bitcrush = 0;
uint32_t stretch_q8 = kStretchQ8One;
uint32_t timestretch_applied_q8 = kStretchQ8One;
uint64_t timestretch_phase_q32 = 0;
uint64_t timestretch_source_inc_q32 = kTimestretchPhaseIncQ32;
TimestretchGrain timestretch_grains[2] = {
    {0, kTimestretchPhaseIncQ32, 0},
    {0, kTimestretchPhaseIncQ32, kGrainHopSamples}};
uint8_t timestretch_audio_now = 128;
bool timestretch_active = false;
bool timestretch_grains_initialized = false;
bool do_lock_clock = false;

// beat tracking (beat = eighth-note)
uint32_t beat_counter = 0;
uint16_t bpm_set = 79;
uint32_t beat_thresh = 21120000;
uint32_t beat_num_total = 0;
bool beat_onset = false;
bool beat_led = 0;
bool btn_reset = 0;
bool soft_sync = 0;
bool is_syncing = false;
bool do_sync_play = false;

// probabilities
uint8_t probability_jump = 0;
uint8_t probability_direction = 0;
uint8_t probability_retrig = 0;
uint8_t probability_gate = 0;
uint8_t probability_tunnel = 0;  // jumps between samples

// retriggering / fx
bool fx_retrig = false;
bool btn_retrig = 0;
uint8_t retrig_sel = 4;
uint8_t retrig_count = 0;
uint8_t retrig_max = 2;
uint8_t retrig_filter = 0;
uint8_t retrig_filter_change = 0;
int8_t retrig_pitch_change = 0;
uint8_t retrig_volume_reduce = 0;
uint8_t button_on = NUM_BUTTONS;
uint8_t button_on2 = 3;
uint8_t button_filter = 0;
bool button_filter_on = false;
uint8_t retrig_volume_reduce_change = 0;
bool retrig_pitch_up = false;
bool retrig_pitch_down = false;
uint8_t syncing_clicks = 0;

// bpm configuring
bool flag_half_time = 0;  // specifies quarter note or not

// noise gate
uint16_t noise_gate_val;
uint16_t noise_gate_thresh;
uint16_t noise_gate_thresh_use;
uint8_t noise_gate_fade = 0;

// buttons
bool button_trigger[8] = {false, false, false, false,
                          false, false, false, false};

// sequencer
Sequencer sequencer;

// midi handler
Onewiremidi *onewiremidi;
int8_t midi_button1 = -1;
int8_t midi_button2 = -1;
volatile bool clock_input_ittybittymidi = false;
volatile bool clock_input_write_pending = false;
volatile bool clock_input_write_value = false;
volatile bool clock_input_write_done = false;
volatile bool clock_input_write_ok = false;

/*
 * HELPER FUNCTIONS
 * knobs / clock in can set these inputs
 *
 */

void param_set_break(uint16_t knob_val, uint8_t &filter_fc_,
                     uint8_t &distortion_, uint8_t &probability_jump_,
                     uint8_t &probability_retrig_, uint8_t &probability_gate_,
                     uint8_t &probability_direction_,
                     uint8_t &probability_tunnel_,
                     uint8_t save_data_[FLASH_PAGE_SIZE]) {
  if (knob_val < 50) {
    // turn it all off
    distortion_ = 0;
    probability_jump_ = 0;
    probability_retrig_ = 0;
    probability_gate_ = 0;
    probability_direction_ = 0;
    probability_tunnel_ = 0;
  } else {
    distortion_ = ease_distortion(knob_val) * DISTORTION_MAX / 255;
    probability_jump_ = ease_probability_jump(knob_val);
    probability_retrig_ = ease_probability_retrig(knob_val);
    probability_gate_ = ease_probability_gate(knob_val);
    probability_direction_ = ease_probability_direction(knob_val);
    probability_tunnel_ = ease_probability_tunnel(knob_val);
  }
  save_data_[SAVE_PROB_JUMP] = probability_jump_;
  save_data_[SAVE_PROB_DIRECTION] = probability_direction_;
  save_data_[SAVE_PROB_RETRIG] = probability_retrig_;
  save_data_[SAVE_PROB_GATE] = probability_gate_;
  save_data_[SAVE_PROB_TUNNEL] = probability_tunnel_;
  save_data_[SAVE_VOLUME] =
      (uint8_t)((distortion_ * 1095 / DISTORTION_MAX + 3000) >> 8);
  save_data_[SAVE_VOLUME + 1] =
      (uint8_t)(distortion_ * 1095 / DISTORTION_MAX + 3000);
}

void param_set_bpm(uint16_t bpm, uint16_t &bpm_set_, uint32_t &beat_thresh_,
                   uint16_t &audio_clk_thresh_) {
  if (bpm > 360) {
    return;
  }
  // set default bpm
  bpm_set_ = bpm;
  // double bpm_fudge = ((double)bpm);
  // calibrated
  double bpm_fudge = ((double)bpm) * 1.054234344 - 1.420118655;
  audio_clk_thresh_ = round(CLOCK_RATE * sample_source_bpm / 250.0 /
                            (SAMPLE_RATE / 1000.0) / bpm_fudge);
  if (audio_clk_thresh_ == 0) {
    audio_clk_thresh_ = 1;
  }
  beat_thresh_ = sample_frames_per_slice * audio_clk_thresh_;
  if (beat_thresh_ == 0) {
    beat_thresh_ = 1;
  }
#ifdef DEBUG_BPM
  printf("new bpm: %d\n", bpm_set_);
  printf("new bpm fudge: %2.3f\n", bpm_fudge);
#endif
}

void param_set_volume(uint16_t knobval, uint8_t &distortion_,
                      uint8_t &volume_reduce_) {
  if (knobval < 2000) {
    distortion_ = 0;
    volume_reduce_ = (2000 - knobval) * (VOLUME_REDUCE_MAX + 3) / 2000;
  } else if (knobval > 3000) {
    volume_reduce_ = 0;
    distortion = (knobval - 3000) * DISTORTION_MAX / (4095 - 3000);
  } else {
    volume_reduce_ = 0;
    distortion = 0;
  }
}

// randint returns value
int randint(int min, int max) {
  int MaxValue = max - min;
  int random_value =
      (int)((1.0 + MaxValue) * rand() /
            (RAND_MAX + 1.0));  // Scale rand()'s return value against RAND_MAX
                                // using doubles instead of a pure modulus to
                                // have a more distributed result.
  return (random_value + min);
}

uint32_t retrig_len(uint8_t index) {
  static const uint16_t retrig_q8[NUM_RETRIGS] = {
      1024, 939, 768, 683, 640, 512, 384, 341, 256, 192,
      171,  128, 96,  85,  64,  48,  32,  24,  16};
  if (index >= NUM_RETRIGS) {
    index = NUM_RETRIGS - 1;
  }
  uint32_t value = (sample_frames_per_slice * retrig_q8[index] + 128u) >> 8u;
  return value > 0 ? value : 1u;
}

uint16_t clamp_gate_thresh(uint32_t value) {
  return value > 0xffffu ? 0xffffu : (uint16_t)value;
}

uint16_t gate_default_thresh() {
  return clamp_gate_thresh(sample_frames_per_slice * 4u);
}

uint16_t gate_scaled_thresh(uint16_t knob_value, uint16_t knob_max) {
  if (knob_max == 0) {
    return 1;
  }
  uint32_t scaled_q1000 = (uint32_t)knob_value * 1000u / knob_max;
  return clamp_gate_thresh(sample_frames_per_slice * scaled_q1000 / 1000u);
}

void refresh_sample_timing(uint16_t sample_index) {
  sample_beats = raw_beats(sample_index);
  if (sample_beats == 0) {
    sample_beats = 1;
  }
  sample_frames_per_slice = raw_len(sample_index) / sample_beats;
  if (sample_frames_per_slice == 0) {
    sample_frames_per_slice = 1;
  }
  sample_source_bpm = piko_audio_sample(sample_index).source_bpm;
  if (sample_source_bpm == 0) {
    sample_source_bpm = BPM_SAMPLED;
  }
}

uint32_t stretch_from_knob_q8(uint16_t knob) {
  const uint64_t eased_knob = static_cast<uint64_t>(knob) * knob * knob;
  const uint64_t eased_max =
      static_cast<uint64_t>(kKnobMax) * kKnobMax * kKnobMax;
  const uint64_t range = kStretchQ8Max - kStretchQ8One;
  return static_cast<uint32_t>(
      kStretchQ8One + ((eased_knob * range) + (eased_max / 2u)) / eased_max);
}

void set_timestretch_knob(uint16_t knob) {
  stretch_q8 = stretch_from_knob_q8(knob);
}

uint64_t wrap_stretch_phase(uint64_t phase_q32, uint32_t frame_count) {
  if (frame_count == 0) {
    return 0;
  }
  const uint64_t loop_len_q32 = static_cast<uint64_t>(frame_count) << 32u;
  while (phase_q32 >= loop_len_q32) {
    phase_q32 -= loop_len_q32;
  }
  return phase_q32;
}

uint64_t subtract_stretch_phase(uint64_t phase_q32, uint64_t amount_q32,
                                uint32_t frame_count) {
  if (frame_count == 0) {
    return 0;
  }
  const uint64_t loop_len_q32 = static_cast<uint64_t>(frame_count) << 32u;
  while (amount_q32 >= loop_len_q32) {
    amount_q32 -= loop_len_q32;
  }
  if (phase_q32 >= amount_q32) {
    return phase_q32 - amount_q32;
  }
  return loop_len_q32 - (amount_q32 - phase_q32);
}

uint32_t grain_window(uint16_t age) {
  if (age >= kGrainLengthSamples) {
    return 0;
  }
  if (age <= kGrainHopSamples) {
    return age;
  }
  return kGrainLengthSamples - age;
}

int16_t read_interpolated_stretch_sample(uint16_t sample_index,
                                         uint64_t phase_q32) {
  const uint32_t frame_count = raw_len(sample_index);
  phase_q32 = wrap_stretch_phase(phase_q32, frame_count);
  const uint32_t frame = static_cast<uint32_t>(phase_q32 >> 32u);
  const uint32_t next_frame = frame + 1u < frame_count ? frame + 1u : 0u;
  const uint32_t frac = static_cast<uint32_t>(phase_q32);

  const int16_t a = static_cast<int16_t>(raw_val(sample_index, frame)) - 128;
  const int16_t b =
      static_cast<int16_t>(raw_val(sample_index, next_frame)) - 128;
  const int32_t diff = static_cast<int32_t>(b) - static_cast<int32_t>(a);
  return static_cast<int16_t>(
      static_cast<int32_t>(a) +
      static_cast<int32_t>((static_cast<int64_t>(diff) * frac) >> 32u));
}

void invalidate_timestretch_grains() {
  timestretch_grains_initialized = false;
}

void initialize_timestretch_grains() {
  const uint32_t frame_count = raw_len(sample);
  timestretch_phase_q32 = wrap_stretch_phase(timestretch_phase_q32, frame_count);
  const uint64_t previous_grain_offset =
      static_cast<uint64_t>(kGrainHopSamples) * kTimestretchPhaseIncQ32;
  timestretch_grains[0] = {timestretch_phase_q32, kTimestretchPhaseIncQ32, 0};
  timestretch_grains[1] = {
      subtract_stretch_phase(timestretch_phase_q32, previous_grain_offset,
                             frame_count),
      kTimestretchPhaseIncQ32, static_cast<uint16_t>(kGrainHopSamples)};
  timestretch_grains_initialized = true;
}

void advance_timestretch_phase_by(uint64_t increment_q32) {
  timestretch_phase_q32 =
      wrap_stretch_phase(timestretch_phase_q32 + increment_q32, raw_len(sample));
}

void accumulate_timestretch_grain(const TimestretchGrain &grain,
                                  int32_t &mixed) {
  const uint32_t weight = grain_window(grain.age);
  if (weight == 0) {
    return;
  }

  const uint64_t grain_phase =
      grain.start_phase_q32 +
      (static_cast<uint64_t>(grain.age) * grain.phase_inc_q32);
  mixed += static_cast<int32_t>(read_interpolated_stretch_sample(sample,
                                                                  grain_phase)) *
           static_cast<int32_t>(weight);
}

void advance_timestretch_grain(TimestretchGrain &grain) {
  ++grain.age;
  if (grain.age < kGrainLengthSamples) {
    return;
  }

  grain.start_phase_q32 = timestretch_phase_q32;
  grain.phase_inc_q32 = kTimestretchPhaseIncQ32;
  grain.age = 0;
}

uint8_t render_stretched_sample() {
  if (!timestretch_grains_initialized) {
    initialize_timestretch_grains();
  }

  int32_t mixed = 0;
  accumulate_timestretch_grain(timestretch_grains[0], mixed);
  accumulate_timestretch_grain(timestretch_grains[1], mixed);

  advance_timestretch_phase_by(timestretch_source_inc_q32);
  advance_timestretch_grain(timestretch_grains[0]);
  advance_timestretch_grain(timestretch_grains[1]);

  const int32_t centered = mixed >> kGrainHopShift;
  const int32_t output = centered + 128;
  if (output < 0) {
    return 0;
  }
  if (output > 255) {
    return 255;
  }
  return static_cast<uint8_t>(output);
}

void reset_retrig_fx() {
  retrig_filter = 0;
  retrig_pitch_up = false;
  retrig_pitch_down = false;
  retrig_pitch_change = 0;
  retrig_volume_reduce = 0;
  retrig_volume_reduce_change = 0;
  button_filter_on = false;
  fx_retrig = false;
  btn_retrig = false;
}

void sync_phase_sample_from_timestretch() {
  const uint32_t frame_count = raw_len(sample);
  timestretch_phase_q32 = wrap_stretch_phase(timestretch_phase_q32, frame_count);
  const uint32_t frame = static_cast<uint32_t>(timestretch_phase_q32 >> 32u);
  phase_sample[phase_head] = frame;
  phase_sample[1 - phase_head] = frame;
  phase_xfade = 0;
}

void update_timestretch_state() {
  const uint32_t target_stretch_q8 = stretch_q8;
  if (target_stretch_q8 < kStretchQ8Bypass) {
    if (timestretch_active) {
      sync_phase_sample_from_timestretch();
      invalidate_timestretch_grains();
    }
    timestretch_active = false;
    timestretch_applied_q8 = kStretchQ8One;
    timestretch_source_inc_q32 = kTimestretchPhaseIncQ32;
    return;
  }

  if (!timestretch_active) {
    timestretch_phase_q32 =
        static_cast<uint64_t>(phase_sample[phase_head] % raw_len(sample)) << 32u;
    timestretch_audio_now = raw_val(sample, phase_sample[phase_head]);
    invalidate_timestretch_grains();
    reset_retrig_fx();
  }

  timestretch_active = true;
  if (target_stretch_q8 != timestretch_applied_q8) {
    timestretch_applied_q8 = target_stretch_q8;
    timestretch_source_inc_q32 =
        (kTimestretchPhaseIncQ32 << 8u) / target_stretch_q8;
  }
}

void sync_timestretch_sample_selection() {
  const uint32_t sample_count = piko_audio_sample_count();
  if (sample_count == 0 || sample_set == sample_change) {
    return;
  }

  sample_set = sample_change % sample_count;
  sample_change = sample_set;
  sample = sample_set;
  sample_add = 0;
  refresh_sample_timing(sample);
  param_set_bpm(bpm_set, bpm_set, beat_thresh, audio_clk_thresh);
  timestretch_phase_q32 =
      wrap_stretch_phase(timestretch_phase_q32, raw_len(sample));
  invalidate_timestretch_grains();
}

/*
 * PWM INTERRUPT LOGIC (main audio thread)
 */
void pwm_interrupt_handler() {
  pwm_clear_irq(pwm_gpio_to_slice_num(AUDIO_PIN));

  if (piko_audio_bank_mutating() || piko_audio_sample_count() == 0) {
    pwm_set_gpio_level(AUDIO_PIN, 128);
    return;
  }

  if ((!do_sync_play && is_syncing) || do_mute) {
    pwm_set_gpio_level(AUDIO_PIN, 128);
    return;
    // bool do_manual_hit = false;
    // if (do_mute) {
    //   if (input_button[1].ChangedHigh(true) ||
    //       input_button[2].ChangedHigh(true) ||
    //       input_button[5].ChangedHigh(true) ||
    //       input_button[6].ChangedHigh(true)) {
    //     soft_sync = true;
    //     do_manual_hit = true;
    //     do_mute_debounce = 0;
    //   }
    // }
    // if (!do_manual_hit) {
    // pwm_set_gpio_level(AUDIO_PIN, 128);
    // return;
    // }
  }

  // clocking when to change beats
  beat_counter++;
  if ((!is_syncing && beat_counter >= beat_thresh) || btn_reset || soft_sync) {
#ifdef DEBUG_CLOCK
    if (soft_sync) {
      printf("softsync; beat_counter: %d, beat_thresh: %d\n", beat_counter,
             beat_thresh);
    }
#endif
    soft_sync = false;
    beat_num_total++;
    beat_counter = 0;
    beat_onset = true;
    beat_led = 1 - beat_led;
    noise_gate_val = 0;
    if (btn_reset) {
      beat_led = 1;
      beat_num_total = 0;
    }
    gpio_put(LED_PIN, beat_led);
    output_trigger.Trigger();

    if (do_mute_debounce > 0) {
      do_mute_debounce--;
    }

#if PIKO_GAMEPI13
    // Pausing the beat-select scan below while Select is held keeps a
    // musical button used as part of "Select + button = jump to mode N"
    // (see the Select handler in main()) from also making the audio engine
    // jump/retrigger on that same press. btn_select only exists under
    // PIKO_GAMEPI13, hence the guard; the original build's gate is always
    // false (never pauses), i.e. unchanged behavior there.
    const bool gamepi_paused_for_select = btn_select.On();
#else
    const bool gamepi_paused_for_select = false;
#endif
    // check button 1
    if (!gamepi_paused_for_select) {
      if (button_on < NUM_BUTTONS) {
        if (!input_button[button_on].On()) {
          // button is off
          button_on = NUM_BUTTONS;
          button_on2 = NUM_BUTTONS;
          select_beat_freeze = 0;
          button_filter_on = false;
          // hm
          retrig_volume_reduce = 0;
          retrig_volume_reduce_change = 0;  // reset

          if (btn_reset) {
            retrig_count = retrig_max;
          }
        }
      } else if (do_mute_debounce == 0) {
        for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
          if (input_button[i].On()) {
            if (button_on >= NUM_BUTTONS) {
              select_beat_freeze = (select_beat / NUM_BUTTONS) * NUM_BUTTONS;
            }
            button_on = i;

// select new beat
#ifdef DEBUG_BUTTONS
            printf("%d on\n", button_on);
#endif
            break;
          }
        }
      }
    }

    // check button 2
    if (!gamepi_paused_for_select) {
      if (button_on2 < NUM_BUTTONS) {
        if (!input_button[button_on2].On()) {
          button_on2 = NUM_BUTTONS;
          button_filter_on = false;
        }
      }
    }
    if (!timestretch_active) {
      // Gated by the same gamepi_paused_for_select as "check button 1"/"check
      // button 2" above: this block reads button_on/button_on2, which are
      // frozen (not updated) while Select is held, per that same pause. Left
      // unguarded, every musical button pressed as part of the "Select +
      // button = jump to mode" gesture got misread as a second button
      // completing a retrigger combo with the stale button_on -- confirmed
      // on hardware as spurious retrigger/break-fx activations. Pausing this
      // block too means no retrigger can arm OR disarm while Select is held,
      // consistent with the already-documented "audio freezes until Select
      // is released" behavior for an already-held musical button.
      if (!gamepi_paused_for_select) {
        if (!btn_retrig) {
          // check button 2
          if (button_on < NUM_BUTTONS && do_mute_debounce == 0) {
            // 1st button pressed, check for second button
            for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
              if (i == button_on) {
                continue;
              }
              if (input_button[i].On()) {
#ifdef DEBUG_BUTTONS
                printf("%d + %d\n", button_on, i);
#endif
                btn_retrig = true;
                button_on2 = i;
              }
            }
          } else {
            if (randint(0, 254) < probability_retrig) {
              btn_retrig = true;
            }
          }
        } else if (btn_retrig) {
          // turn off retrig if one of the buttons is released
          if (button_on == NUM_BUTTONS || button_on2 == NUM_BUTTONS) {
            retrig_count = retrig_max;
          }
        }
      }
    } else {
      reset_retrig_fx();
    }
    if (!fx_retrig) {
#ifdef DEBUG_PWM
      printf("[%d bpm / %d thresh / beat_num: %d] ", bpm_set, beat_thresh,
             beat_num_total);
#endif

      // check for fx
      if (btn_retrig && !fx_retrig) {
#ifdef DEBUG_PWM
        printf("\n");
#endif
        fx_retrig = true;
        uint8_t r1 = randint(0, 100);
        uint8_t r2 = randint(0, 100);
        uint8_t r3 = randint(0, 100);
        uint8_t r4 = randint(0, 100);
        retrig_count = 0;
        // retrig_sel = randint(0, 11);
        // if (retrig_sel == 4) {
        //   retrig_sel = 5;
        // }
        if (button_on2 >= NUM_BUTTONS) {
          retrig_sel = randint(2, 16);
        } else {
          bool exact_retrig = false;
#if PIKO_GAMEPI13
          // Holding Start at the exact instant a 2-button retrigger fires
          // fixes the subdivision instead of sorting it, for predictable
          // live control. Reuses the button-held-as-modifier flag so
          // releasing Start afterward doesn't also trigger the mute/
          // start-stop toggle (same pattern the Function A/B L/R block
          // already uses).
          if (btn_start.On()) {
            exact_retrig = true;
            gamepi_start_used_as_modifier = true;
          }
#endif
          if (exact_retrig) {
            // Midpoint of the same window sorted below, per button_on2 --
            // keeps the existing "button 0 = slowest, button 7 = fastest"
            // feel, just removes the randomness.
            static const uint8_t kExactRetrigSel[8] = {1, 3, 5, 7, 9, 11, 13, 15};
            retrig_sel = kExactRetrigSel[button_on2];
          } else {
            switch (button_on2) {
              case 0:
                retrig_sel = randint(0, 2);
                break;
              case 1:
                retrig_sel = randint(2, 4);
                break;
              case 2:
                retrig_sel = randint(4, 6);
                break;
              case 3:
                retrig_sel = randint(6, 8);
                break;
              case 4:
                retrig_sel = randint(8, 10);
                break;
              case 5:
                retrig_sel = randint(10, 12);
                break;
              case 6:
                retrig_sel = randint(12, 14);
                break;
              case 7:
                retrig_sel = randint(14, 16);
                break;
            }
          }
        }
        retrig_max = randint(3, 16);
        if (retrig_sel < 6) {
          retrig_max = retrig_max / 2;
        } else if (retrig_sel > 11) {
          retrig_max = retrig_max * 2;
        }
        if (r1 <= 15) {
          retrig_pitch_up = true;
        } else if (r2 <= 15) {
          retrig_pitch_down = true;
        }
        if (r3 < 30) {
          retrig_filter = retrig_max;
          retrig_filter_change = (LPF_MAX - 10) / retrig_max;
        }
        if (r4 < 20 && retrig_sel > 6) {
          retrig_volume_reduce = retrig_max;
          if (retrig_volume_reduce > 5) {
            retrig_volume_reduce = 5;
          }
          retrig_volume_reduce_change = 1;  // volume increases
          if (randint(1, 100) < 30) {
            // delay fx
            retrig_volume_reduce_change = 2;  // volume decreases
            retrig_volume_reduce = 1;
          }
        }
        audio_clk = audio_clk_thresh - 1;
        phase_retrig = (retrig_len(retrig_sel) << flag_half_time) - 1;
      }
    }
  }

  // disable beat interrupts during fx
  if (fx_retrig && !timestretch_active) {
    beat_onset = false;
  }

  // clocking when to change samples
  audio_clk++;
  int32_t audio_tick_thresh = audio_clk_thresh;
  if (!timestretch_active) {
    audio_tick_thresh += retrig_pitch_change;
  }
  if (audio_tick_thresh < 1) {
    audio_tick_thresh = 1;
  }
  const bool audio_tick = audio_clk >= static_cast<uint16_t>(audio_tick_thresh);
  if (!audio_tick && !beat_onset) {
    pwm_set_gpio_level(AUDIO_PIN, audio_now);
    return;
  }

  update_timestretch_state();

  if (audio_tick || beat_onset) {
    if (timestretch_active) {
      if (audio_tick) {
        audio_clk = 0;
        sync_timestretch_sample_selection();
        noise_gate_val++;
        if (noise_gate_val < 10 & noise_gate_fade > 0) {
          noise_gate_fade--;
        } else if (noise_gate_val > noise_gate_thresh_use) {
          if (noise_gate_val % 100 == 0 && noise_gate_fade < 8) {
            noise_gate_fade++;
          }
        }
        timestretch_audio_now = render_stretched_sample();
        sync_phase_sample_from_timestretch();
      }
      if (beat_onset) {
        beat_onset = false;
        btn_reset = 0;
      }
    } else {
      audio_clk = 0;
      // beat onset causes next sample
      if (beat_onset && fx_retrig == false) {
        bool do_switch_heads = true;

        if (probability_tunnel > 0) {
          if (randint(0, 255) < probability_tunnel) {
            sample_add = randint(0, piko_audio_sample_count() - 1);
          } else {
            sample_add = 0;
          }
        } else {
          sample_add = 0;
        }
        if (sample_set != sample_change) {
          sample_set = sample_change;
        }
        sample = (sample_set + sample_add) % piko_audio_sample_count();
        refresh_sample_timing(sample);
        param_set_bpm(bpm_set, bpm_set, beat_thresh, audio_clk_thresh);

        beat_onset = false;
        if (do_lock_clock) {
          select_beat = beat_num_total % sample_beats;
        } else {
          select_beat++;
        }
        if (flag_half_time) {
          select_beat++;
          if (select_beat % 2 > 0)
            select_beat++;  // make sure for halftime mode its only on the even
                            // beats
        }

        if (select_beat < 0) {
          do_switch_heads = false;
          select_beat = sample_beats - 1;
        }
        if (select_beat >= sample_beats) {
          do_switch_heads = false;
          select_beat = 0;
        }

        // random jumps
        if (probability_jump > 0) {
          if (randint(0, 255) < probability_jump) {
            select_beat = randint(0, sample_beats - 1);
          }
        }

        // random gate
        if (probability_gate > 0) {
          if (randint(0, 255) < probability_gate) {
            noise_gate_thresh_use =
                sample_frames_per_slice * randint(800, 1000) / 1000;
          } else {
            noise_gate_thresh_use = noise_gate_thresh;
          }
        } else {
          noise_gate_thresh_use = noise_gate_thresh;
        }

        // reset
        if (btn_reset) {
          btn_reset = 0;
          select_beat = 0;
        }
        // printf("button_on: %d\n", button_on);
        // printf("button_on2: %d\n", button_on2);
        // printf("select_beat: %d\n", select_beat);

        // get beat from sequencer
        if (sequencer.IsPlaying()) {
          select_beat = sequencer.Next(beat_num_total);
#ifdef DEBUG_SEQUENCER
          printf("sequencer: [%d] %d\n", sequencer.NextI(beat_num_total),
                 select_beat);
#endif
        }

        // hold button down to play that beat
        if (button_on < NUM_BUTTONS) {
          select_beat = (button_on + select_beat_freeze) % sample_beats;
          // record the current beat
          sequencer.Record(select_beat);
        }
#ifdef DEBUG_PWM
        printf("select_beat:%d for %d samples\n", select_beat,
               retrig_len(retrig_sel) << flag_half_time);
#endif
        MidiOut_on(midiout, midi_notes_set[(select_beat % 8)], 127);

        if (do_switch_heads) {
          phase_head = 1 - phase_head;  // switch heads
          phase_xfade = 1 << HEAD_SHIFT;
        }
        phase_sample[phase_head] =
            select_beat * (sample_frames_per_slice << flag_half_time);

        // random direction for the new head
        if (probability_direction > 0) {
          uint8_t r1 = randint(0, 255);
          if (direction[phase_head] == base_direction) {
            if (r1 < probability_direction) {
              direction[phase_head] = 1 - base_direction;
            }
          } else {
            if (r1 > probability_direction) {
              direction[phase_head] = base_direction;
            }
          }
        } else {
          direction[phase_head] = base_direction;
        }
      } else {
        // update the sample
        noise_gate_val++;
        if (noise_gate_val < 10 & noise_gate_fade > 0) {
          // noise gate fade in
          noise_gate_fade--;
        } else if (noise_gate_val > noise_gate_thresh_use) {
          // noise gate fade out
          if (noise_gate_val % 100 == 0) {
            if (noise_gate_fade < 8) {
              noise_gate_fade++;
            }
          }
        }
        for (uint8_t i = 0; i < 2; i++) {
          if (direction[i]) {
            phase_sample[i]++;
            if (phase_sample[i] == raw_len(sample) - 1) {
              phase_sample[i] = 0;
            }
          } else {
            if (phase_sample[i] == 0) {
              phase_sample[i] = raw_len(sample) - 2;
            } else {
              phase_sample[i]--;
            }
          }
        }
      }

      if (fx_retrig) {
        phase_retrig++;

        // prevent noise gating?
        noise_gate_fade = 0;
        noise_gate_val = 0;

        if (phase_retrig % (retrig_len(retrig_sel) << flag_half_time) == 0) {
          retrig_count++;
          if (retrig_filter > 0) {
            retrig_filter--;
          }

          MidiOut_on(midiout, midi_notes_set[(select_beat % 8)],
                     120 * retrig_count / retrig_max);

          // printf("retrig_volume_reduce_change: %d\n",
          //        retrig_volume_reduce_change);
          // printf("retrig_volume_reduce: %d\n", retrig_volume_reduce);

          if (retrig_volume_reduce_change == 1 && retrig_volume_reduce > 0) {
            if (retrig_sel > 11) {
              if (retrig_count % 2 == 0) {
                retrig_volume_reduce--;
              }
            } else {
              retrig_volume_reduce--;
            }
          } else if (retrig_volume_reduce_change == 2 &&
                     retrig_volume_reduce < 8 && retrig_count % 2 == 0) {
            if (retrig_sel > 11) {
              if (retrig_count % 4 == 0) {
                retrig_volume_reduce++;
              }
            } else {
              retrig_volume_reduce++;
            }
          }
          if (retrig_pitch_up) {
            retrig_pitch_change++;
          } else if (retrig_pitch_down) {
            retrig_pitch_change--;
          }
          if (retrig_count >= retrig_max) {
            reset_retrig_fx();
          }
#ifdef DEBUG_PWM
          printf(
              "[retrig %d/%d] select_beat:%d for %d samples, beat_counter: %d, "
              "\n\tphase_sample[phase_head]: %d%%%d==0\n",
              retrig_count, retrig_max, select_beat,
              retrig_len(retrig_sel) << flag_half_time, beat_counter,
              phase_sample[phase_head],
              (retrig_len(retrig_sel) << flag_half_time));
#endif
          // setup
          phase_head = 1 - phase_head;  // switch heads
          phase_xfade = 1 << HEAD_SHIFT;
          phase_sample[phase_head] =
              select_beat * (sample_frames_per_slice << flag_half_time);
          phase_retrig = 0;
        }
      }
    }
  }

  // determine sample
  if (timestretch_active) {
    audio_now = timestretch_audio_now;
  } else {
    if (phase_xfade == 0) {
      audio_now = raw_val(sample, phase_sample[phase_head]);
    } else {
      phase_xfade--;

      // new head
      uint32_t u = (uint32_t)raw_val(sample, phase_sample[phase_head]);
      u = u * ((1 << HEAD_SHIFT) - phase_xfade);  // fade it in

      // old head
      uint32_t v = (uint32_t)raw_val(sample, phase_sample[1 - phase_head]);
      v = v * phase_xfade;  // fade it out

      // combine
      u = (u + v) >> HEAD_SHIFT;

      // set to audio now
      audio_now = (uint8_t)u;
      // if (phase_xfade == 1 << HEAD_SHIFT - 1) {
      //   // printf("\nphase_head: %d; audio_now=%d\n", phase_head, u);
      // }
    }
  }

    // <volume>
    if (volume_reduce >= VOLUME_REDUCE_MAX) audio_now = 128;
    if (audio_now != 128) {
      // distortion / wave-folding
      if (distortion > 0) {
        if (audio_now > 128) {
          if (audio_now < (255 - distortion)) {
            audio_now += distortion;
          } else {
            audio_now = 255 - distortion;
          }
          audio_now = 128 + ((audio_now - 128) / ((distortion >> 4) + 1));
        } else {
          if (audio_now > distortion) {
            audio_now -= distortion;
          } else {
            audio_now = distortion - audio_now;
          }
          audio_now = 128 - ((128 - audio_now) / ((distortion >> 4) + 1));
        }
      }
      // reduce volume
      if (volume_reduce > 0) {
        if (audio_now > 128) {
          audio_now = audio_now - (volume_reduce);
          if (audio_now < 128) audio_now = 128;
        } else {
          audio_now = audio_now + (volume_reduce);
          if (audio_now > 128) audio_now = 128;
        }
      }
      if ((volume_mod + retrig_volume_reduce + noise_gate_fade) > 0 &&
          audio_now != 128) {
        if (audio_now > 128) {
          audio_now = ((audio_now - 128) >>
                       (volume_mod + retrig_volume_reduce + noise_gate_fade)) +
                      128;
        } else {
          audio_now =
              128 - ((128 - audio_now) >>
                     (volume_mod + retrig_volume_reduce + noise_gate_fade));
        }
      }
    }  // </volume>

    // <bitcrush>
    // if (bitcrush > 0) {
    //   if (audio_now > 128) {
    //     audio_now = 128 + (((audio_now - 128) >> bitcrush) << bitcrush);
    //   } else if (audio_now < 128) {
    //     audio_now = 128 - (((128 - audio_now) >> bitcrush) << bitcrush);
    //   }
    // }
    // </bitcrush>

    // <filter>
    if ((filter_fc - (retrig_filter * retrig_filter_change) - button_filter) <=
        LPF_MAX) {
      audio_now = (uint8_t)filter_lpf(
          (int64_t)audio_now,
          (filter_fc - (retrig_filter * retrig_filter_change) - button_filter),
          filter_q);
      // } else {
      // audio_now = (uint8_t)filter_lpf((int64_t)audio_now, LPF_MAX, filter_q);
    }
    // </filter>

    // <delay>
    // audio_now = delay.Update(audio_now);
    // </delay>

    // <dither>
    // audio_now = ditherer.Update(audio_now);
    // </dither>
  pwm_set_gpio_level(AUDIO_PIN, audio_now);
}

void print_buf(const uint8_t *buf, size_t len) {
  for (size_t i = 0; i < len; ++i) {
    printf("%02x", buf[i]);
    if (i % 24 == 23)
      printf("\n");
    else
      printf(" ");
  }
}

void do_stop_everything() { do_mute = true; }
void do_start_everything() {
  // reset syncing
  is_syncing = false;
  syncing_clicks = 0;
  do_mute_debounce = 8;
  button_on = NUM_BUTTONS;
  button_on2 = NUM_BUTTONS;
  btn_reset = true;
  // reset everything
  // reset retrig stuff
  retrig_filter = 0;
  retrig_pitch_up = false;
  retrig_pitch_down = false;
  retrig_pitch_change = 0;
  retrig_volume_reduce = 0;
  retrig_volume_reduce_change = 0;
  button_filter_on = false;
  fx_retrig = false;
  btn_retrig = false;
  do_mute = false;
}

uint32_t current_time() { return to_ms_since_boot(get_absolute_time()); }

void service_usb_startup(uint32_t timeout_ms) {
  const absolute_time_t deadline = make_timeout_time_ms(timeout_ms);
  while (!time_reached(deadline)) {
    tud_task();
    if (tud_mounted()) {
      return;
    }
    sleep_ms(1);
  }
}

uint16_t *sort_int32_t(uint32_t array[], int n) {
  // C
  // uint16_t *indexes = malloc(sizeof(uint16_t) * n);
  // C++
  uint16_t *indexes = new uint16_t[n];
  for (int i = 0; i < n; i++) {
    indexes[i] = i;
  }
  // Sort the auxiliary array based on the values in the original array.
  for (int i = 0; i < n - 1; i++) {
    for (int j = i + 1; j < n; j++) {
      if (array[indexes[i]] > array[indexes[j]]) {
        // Swap the elements at indexes[i] and indexes[j].
        int temp = indexes[i];
        indexes[i] = indexes[j];
        indexes[j] = temp;
      }
    }
  }
  return indexes;
}

#define MIDI_MAX_NOTES 128
#define MIDI_MAX_TIME_ON 10000  // 10 seconds

uint32_t note_hit[MIDI_MAX_NOTES];
bool note_on[MIDI_MAX_NOTES];
uint32_t midi_last_time = 0;
uint32_t midi_delta_sum = 0;
uint32_t midi_delta_count = 0;
#define MIDI_DELTA_COUNT_MAX 32
uint32_t midi_timing_count = 0;
const uint8_t midi_timing_modulus = 24;

void midi_note_off(uint8_t note) {
#ifdef DEBUG_MIDI
  printf("note_off: %d\n", note);
#endif
#if MIDI_NOTE_KEY == 1
  input_button[note % NUM_BUTTONS].Set(false);
  if (midi_button2 > -1) {
    midi_button2 = -1;
  } else {
    midi_button1 = -1;
  }
#endif
}

void midi_note_on(uint8_t note, uint8_t velocity) {
#ifdef DEBUG_MIDI
  printf("note_on: %d\n", note);
#endif
#if MIDI_NOTE_KEY == 1
  if (midi_button1 > -1) {
    midi_button2 = note % NUM_BUTTONS;
  } else {
    midi_button1 = note % NUM_BUTTONS;
  }
  input_button[note % NUM_BUTTONS].Set(true);
#endif
}

void midi_start() {
#ifdef DEBUG_MIDI
  printf("midi start\n");
#endif
  do_start_everything();
  soft_sync = false;
  btn_reset = false;
  midi_timing_count = 24 * MIDI_RESET_EVERY_BEAT - 1;
}
void midi_continue() {
#ifdef DEBUG_MIDI
  printf("midi continue (starting)\n");
#endif
  do_start_everything();
  soft_sync = false;
  btn_reset = false;
  midi_timing_count = 24 * MIDI_RESET_EVERY_BEAT - 1;
}
void midi_stop() {
#ifdef DEBUG_MIDI
  printf("midi stop\n");
#endif
  do_stop_everything();
  soft_sync = false;
  btn_reset = false;
  midi_timing_count = 24 * MIDI_RESET_EVERY_BEAT - 1;
}
void midi_timing() {
  midi_timing_count++;
  if (midi_timing_count % (24 * MIDI_RESET_EVERY_BEAT) == 0) {
    btn_reset = true;
#ifdef DEBUG_MIDI
    printf("midi resetting");
#endif
  } else if (midi_timing_count %
                 (midi_timing_modulus / MIDI_CLOCK_MULTIPLIER) ==
             0) {
    soft_sync = true;
  }
  uint32_t now_time = time_us_32();
  if (midi_last_time > 0) {
    midi_delta_sum += now_time - midi_last_time;
    midi_delta_count++;
    if (midi_delta_count == MIDI_DELTA_COUNT_MAX) {
      uint32_t bpm_input =
          (int)round(1250000.0 * MIDI_CLOCK_MULTIPLIER * MIDI_DELTA_COUNT_MAX /
                     (float)(midi_delta_sum));
#ifdef DEBUG_MIDI
      printf("midi bpm\t%d\n", bpm_input);
#endif
      if (bpm_input - 7 != bpm_set) {
        // #ifdef DEBUG_CLOCK
        //         printf("%d, %d\n", clock_sync_ms, bpm_input);
        // #endif
        // REDUCE THE BPM INPUT TO ELIMINATE OVERSTEPPING
        param_set_bpm(bpm_input - 7, bpm_set, beat_thresh, audio_clk_thresh);
      }
      midi_delta_count = 0;
      midi_delta_sum = 0;
    }
  }
  midi_last_time = now_time;
}

void reset_clock_input_state() {
  syncing_clicks = 0;
  is_syncing = false;
  do_sync_play = false;
  soft_sync = false;
  btn_reset = true;
  midi_last_time = 0;
  midi_delta_sum = 0;
  midi_delta_count = 0;
  midi_timing_count = 24 * MIDI_RESET_EVERY_BEAT - 1;
}

bool piko_clock_input_ittybittymidi() {
  return clock_input_ittybittymidi;
}

bool piko_set_clock_input_ittybittymidi(bool enabled) {
  clock_input_write_done = false;
  clock_input_write_ok = false;
  clock_input_write_value = enabled;
  __asm volatile("dmb" ::: "memory");
  clock_input_write_pending = true;

  const absolute_time_t deadline = make_timeout_time_ms(2000);
  while (!clock_input_write_done && !time_reached(deadline)) {
    sleep_ms(1);
  }
  return clock_input_write_done && clock_input_write_ok;
}

int main(void) {
  // Set the final system clock before USB init.
  set_sys_clock_khz(CLOCK_RATE, true);
  tusb_init();
  irq_set_priority(USBCTRL_IRQ, 0x00);
  piko_audio_bank_init();
  stdio_init_all();

  // sleep needed to make sure it can start on battery
  // not sure why
  sleep_ms(100);

  if (piko_audio_sample_count() > 0) {
    refresh_sample_timing(0);
  }

  // initialize bpm
  param_set_bpm(BPM_SAMPLED, bpm_set, beat_thresh, audio_clk_thresh);

  // initialize leds
  ledarray.Init();

  service_usb_startup(1500);
  // Register core0 as the multicore_lockout "victim" so PikoSampleManager
  // (running on core1) can safely pause it during flash_range_erase/program
  // calls -- both cores otherwise fetch instructions from the same flash
  // over XIP continuously (the audio PWM ISR alone runs ~988kHz), and
  // erasing/programming without pausing the other core is a documented
  // pico-sdk hazard that can corrupt the write. Must be called here, before
  // core1 launches and can ever call multicore_lockout_start_blocking().
#if PIKO_GAMEPI13
  gamepi_spi1_mutex_init();
#endif
  multicore_lockout_victim_init();
  multicore_launch_core1(piko_sample_manager_core);

  // initialize clocking and PWM interrupts
  // overclock at a multiple of sampling rate
  gpio_set_function(AUDIO_PIN, GPIO_FUNC_PWM);
  int audio_pin_slice = pwm_gpio_to_slice_num(AUDIO_PIN);
  pwm_clear_irq(audio_pin_slice);
  irq_set_priority(PWM_IRQ_WRAP, 0xc0);
  irq_set_exclusive_handler(PWM_IRQ_WRAP, pwm_interrupt_handler);
  pwm_set_irq_enabled(audio_pin_slice, false);
  irq_set_enabled(PWM_IRQ_WRAP, false);
  pwm_config config = pwm_get_default_config();
  /*
   * clock fires 176 Mhz
   * with wrap set to 250
   * at clock division of 1
   * = 704 kHz
   * so 22 kHz sampled audio needs a new sample
   * every 32 pulses
   */
  pwm_config_set_clkdiv(&config, 1.0f);
  pwm_config_set_wrap(&config, 250);
  pwm_init(audio_pin_slice, &config, true);
  pwm_set_gpio_level(AUDIO_PIN, 0);

  // setup gpio pins
  gpio_init(LED_PIN);
  gpio_set_dir(LED_PIN, GPIO_OUT);
  gpio_init(CLOCK_PIN);
  gpio_set_dir(CLOCK_PIN, GPIO_IN);
#if PIKO_GAMEPI13
  // GP22 has no external clock-jack circuit on the GamePi13 board (unlike
  // pikocore's original PCB, where the jack's own analog frontend normalizes
  // the idle/unplugged state to a defined level). A bare internal pull-down
  // here leaves the pin idle LOW, which the "1 - gpio_get()" inversion below
  // reads as a permanent false clock pulse, latching audio into permanent
  // silence shortly after boot (do_sync_play never toggles true again).
  // Pull up instead so idle reads HIGH -> inverted 0, matching the polarity
  // the edge-detection logic expects when no external clock is connected.
  gpio_pull_up(CLOCK_PIN);
#else
  gpio_pull_down(CLOCK_PIN);
#endif
#if !PIKO_GAMEPI13
  // Pico power-save pin; on the GamePi13, GP23 is the L button.
  gpio_init(23);
  gpio_pull_up(23);
  gpio_set_dir(23, GPIO_OUT);
  gpio_put(23, 0);
#endif

  // initialize buttons
#if PIKO_GAMEPI13
  const uint8_t gamepi_button_pins[NUM_BUTTONS] = GAMEPI_BUTTON_PINS;
  for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
    input_button[i].Init(gamepi_button_pins[i], 10);
  }
#else
  for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
    input_button[i].Init(i + 4, 10);  // GPIO 4 through 11 are buttons
  }
#endif

  // initialize knobs
#if PIKO_GAMEPI13
  for (uint8_t i = 0; i < NUM_KNOBS; i++) {
    input_knob[i].Init(i, 50);
  }
  btn_select.Init(GAMEPI_BTN_SELECT, 10);
  btn_start.Init(GAMEPI_BTN_START, 10);
  btn_l.Init(GAMEPI_BTN_L, 10);
  btn_r.Init(GAMEPI_BTN_R, 10);
  gamepi_ui_init();
#else
  adc_init();
  for (uint8_t i = 0; i < NUM_KNOBS; i++) {
    input_knob[i].Init(i, 50);
  }
#endif

  // initialize midi out
  midiout = MidiOut_malloc(0, true);

  // initialize sequencer
  sequencer.Init();

  // initialize save data
  uint8_t save_data[FLASH_PAGE_SIZE];
  for (uint32_t i = 0; i < FLASH_PAGE_SIZE; ++i) {
    save_data[i] = 0;
  }
  // // save defaults that aren't defaulted to 0
  save_data[SAVE_VOLUME] = (uint8_t)(2500 >> 8);
  save_data[SAVE_VOLUME + 1] = (uint8_t)2500;
  save_data[SAVE_BPM] = (uint8_t)(165 >> 8);
  save_data[SAVE_BPM + 1] = (uint8_t)165;
  noise_gate_thresh = gate_default_thresh();
  noise_gate_thresh_use = noise_gate_thresh;
  save_data[SAVE_GATE] = (uint8_t)(noise_gate_thresh >> 8);
  save_data[SAVE_GATE + 1] = (uint8_t)noise_gate_thresh;
  save_data[SAVE_CLOCK_INPUT_MODE] = CLOCK_INPUT_CLOCK;

  // initializer trigger
  output_trigger.Init(TRIGO_PIN, 10, MAIN_LOOP_HZ);

  // initialize control loop variables
  uint32_t clock_ms = 0;
  uint32_t bpm_input = 165;
  uint32_t clock_hits = 0;
  uint32_t clock_sync_ms = 0;
  uint16_t alpha0 = 500;
  uint8_t selector_knob = 0;
  uint16_t ledarray_sel = 0;
  uint32_t ledarray_sel_debounce = 0;
  uint16_t ledarray_save = 0;
  uint16_t ledarray_load = 0;
  uint32_t ledarray_binary_debounce = 0;
  uint8_t ledarray_binary = 0;

  // debouncing
  uint16_t debounce_sample = 0;
  uint16_t debounce_lock_clock = 0;
  uint32_t debounce_saving = 0;
  uint32_t debounce_led_save = 0;
  uint8_t debounce_led_sequencer = 0;
  uint8_t debounce_led_load = 0;
  uint8_t clock_pin_last = 0;
  uint8_t last_button_on = NUM_BUTTONS;
  bool has_saved = false;
  bool do_load = false;
  // El load al bootear y el load del usuario (modo 6) comparten el mismo
  // bloque, pero no pueden aplicar el sample igual: ver el comentario en el
  // bloque de carga.
  bool load_is_boot = false;
  bool first_time = false;
  bool has_loaded = false;
  RunningAverage ra;
  ra.Init(5);

  auto reset_clock_timing = [&]() {
    clock_sync_ms = 0;
    clock_hits = 0;
    clock_pin_last = 0;
    ra.Init(5);
    reset_clock_input_state();
  };

  auto save_settings = [&]() {
    save_data[FLASH_PAGE_SIZE - 1] = 0x01;
    save_data[FLASH_PAGE_SIZE - 2] = 0x02;
    save_data[FLASH_PAGE_SIZE - 3] = 0x03;
    save_data[FLASH_PAGE_SIZE - 4] = 0x04;
#if PIKO_GAMEPI13
    // El modo actual todavía tiene sus valores "vivos" en input_knob -- la
    // tabla por modo solo se actualiza al CAMBIAR de modo, así que hay que
    // volcarlos antes de serializar o se guardaría el valor previo.
    gamepi_store_mode_knobs(gamepi_selector);
    for (uint8_t m = 0; m < 8; m++) {
      for (uint8_t k = 0; k < 2; k++) {
        const uint16_t v = gamepi_knob_by_mode[m][k];
        const uint16_t off = (uint16_t)(SAVE_KNOB_BY_MODE + (m * 2 + k) * 2);
        save_data[off] = (uint8_t)(v >> 8);
        save_data[off + 1] = (uint8_t)v;
      }
    }
    save_data[SAVE_KNOB_MAGIC] = SAVE_KNOB_MAGIC_VALUE;
#endif
    // El filtro ya se escribe en SAVE_FILTER cada vez que cambia; el mágico
    // marca que este save lo trae de verdad (los anteriores tienen 0 ahí).
    save_data[SAVE_FILTER] = filter_fc;
    save_data[SAVE_FILTER_MAGIC] = SAVE_FILTER_MAGIC_VALUE;
    sequencer.Save(save_data);
#ifdef DEBUG_SAVE
    print_buf(save_data, FLASH_PAGE_SIZE);
#endif
    uint32_t ints = save_and_disable_interrupts();
    flash_range_erase(PIKO_SETTINGS_FLASH_OFFSET, FLASH_SECTOR_SIZE);
    flash_range_program(PIKO_SETTINGS_FLASH_OFFSET, save_data, FLASH_PAGE_SIZE);
    restore_interrupts(ints);
  };

  // initialize one wire midi
  onewiremidi =
      Onewiremidi_new(pio1, 0, CLOCK_PIN, midi_note_on, midi_note_off,
                      midi_start, midi_continue, midi_stop, midi_timing);

// LED
#if WS2812_ENABLED == 1
  WS2812 ledStrip(
      23,    // Data line is connected to pin 0. (GP0)
      1,     // Strip is 6 LEDs long.
      pio0,  // Use PIO 0 for creating the state machine.
      0,  // Index of the state machine that will be created for controlling the
          // LED strip You can have 4 state machines per PIO-Block up to 8
          // overall. See Chapter 3 in:
          // https://datasheets.raspberrypi.org/rp2040/rp2040-datasheet.pdf
      WS2812::FORMAT_GRB
  );
#endif

  piko_sample_manager_set_ready();
  pwm_clear_irq(audio_pin_slice);
  pwm_set_irq_enabled(audio_pin_slice, true);
  irq_set_enabled(PWM_IRQ_WRAP, true);

  // control loop
  while (1) {
    __wfi();  // Wait for Interrupt
    clock_ms++;
    clock_sync_ms++;

    if (clock_input_ittybittymidi) {
      Onewiremidi_receive(onewiremidi);
    }
#if WS2812_ENABLED == 1
    if (clock_ms % 200 == 0) {
      const uint8_t knob_a_led =
          input_knob[1].Value() * 120 / input_knob[1].ValueMax();
      const uint8_t knob_b_led =
          input_knob[2].Value() * 120 / input_knob[2].ValueMax();
      if (debounce_led_save > 0) debounce_led_save--;
      if (debounce_lock_clock > 0) debounce_lock_clock--;
      if (sequencer.IsPlaying() && debounce_led_sequencer > 0) {
        debounce_led_sequencer--;
      }
      if (debounce_led_load > 0) debounce_led_load--;
      ledStrip.fill(WS2812::RGB(knob_a_led, 0, knob_b_led));
      ledStrip.show();
    }
#endif

    if (debounce_sample > 0) {
      debounce_sample--;
    }
    if (clock_input_write_pending) {
      const bool requested = clock_input_write_value;
      clock_input_write_pending = false;
      clock_input_ittybittymidi = requested;
      save_data[SAVE_CLOCK_INPUT_MODE] =
          requested ? CLOCK_INPUT_MIDI : CLOCK_INPUT_CLOCK;
      reset_clock_timing();
      save_settings();
      clock_input_write_ok = true;
      clock_input_write_done = true;
    }
    // flash works
    if (debounce_saving > 0 && clock_ms > 64000) {
      debounce_saving--;
      if (debounce_saving == 0) {
#ifdef DEBUG_SAVE
        printf("\nsaving:\n");
#endif
        save_settings();
#if PIKO_GAMEPI13
        gamepi_state_saved_us = time_us_64();
        gamepi_state_in_sync = true;
        gamepi_clear_state_bars();
#endif
#ifdef DEBUG_SAVE
        printf("saved!\n");
#endif
      }
    }
    if (clock_ms == 100) {
      do_load = true;
      load_is_boot = true;
      first_time = true;
    }
    if (do_load) {
      do_load = false;
      ledarray_load = 16000;
      debounce_saving = 0;
#ifdef DEBUG_SAVE
      printf("\n\n\nPICO_FLASH_SIZE_BYTES: \t%d\n", PICO_FLASH_SIZE_BYTES);
      printf("PIKO_SETTINGS_FLASH_OFFSET: \t%d\n", PIKO_SETTINGS_FLASH_OFFSET);
      printf("FLASH_PAGE_SIZE: \t%d\n", FLASH_PAGE_SIZE);
      printf("FLASH_SECTOR_SIZE: \t%d\n", FLASH_SECTOR_SIZE);
      printf("XIP_BASE: \t%d\n", XIP_BASE);
      printf("save data:\n");
      print_buf(flash_target_contents, FLASH_PAGE_SIZE);
      printf("\nloading saved data: \n");
#endif
      if (flash_target_contents[FLASH_PAGE_SIZE - 1] == 0x01 &&
          flash_target_contents[FLASH_PAGE_SIZE - 2] == 0x02 &&
          flash_target_contents[FLASH_PAGE_SIZE - 3] == 0x03 &&
          flash_target_contents[FLASH_PAGE_SIZE - 4] == 0x04) {
        for (uint i = 0; i < FLASH_PAGE_SIZE; i++) {
          save_data[i] = flash_target_contents[i];
        }
        param_set_volume((uint16_t)(save_data[SAVE_VOLUME] << 8) +
                             save_data[SAVE_VOLUME + 1],
                         distortion, volume_reduce);
        // Filtro: solo si el save lo trae (ver SAVE_FILTER_MAGIC). Clamp al
        // rango válido por si la flash quedó corrupta -- un filter_fc fuera de
        // rango indexaría mal la tabla de coeficientes del biquad.
        if (save_data[SAVE_FILTER_MAGIC] == SAVE_FILTER_MAGIC_VALUE) {
          filter_fc = save_data[SAVE_FILTER];
          if (filter_fc > LPF_MAX + 10) filter_fc = LPF_MAX + 10;
        }
        sample_change = save_data[SAVE_SAMPLE];
        if (piko_audio_sample_count() > 0) {
          sample_change %= piko_audio_sample_count();
          if (load_is_boot) {
            // Al bootear no hay nada sonando y la ISR necesita timing válido
            // desde el primer sample, así que se aplica directo.
            sample = sample_change;
            refresh_sample_timing(sample);
          }
          // Load del usuario: NO se toca `sample` ni su timing. Dejar sólo
          // sample_change hace que la ISR lo adopte en el próximo beat onset
          // -- el mismo camino que un cambio de sample manual, que por eso no
          // corta. Asignarlo acá, a mitad de reproducción, era lo que hacía
          // "reiniciar el playback" al cargar un estado.
        } else {
          sample_change = 0;
          sample = 0;
        }
        param_set_bpm(
            (uint16_t)(save_data[SAVE_BPM] << 8) + save_data[SAVE_BPM + 1],
            bpm_set, beat_thresh, audio_clk_thresh);
        noise_gate_thresh =
            (uint16_t)(save_data[SAVE_GATE] << 8) + save_data[SAVE_GATE + 1];
        probability_direction = save_data[SAVE_PROB_DIRECTION];
        probability_jump = save_data[SAVE_PROB_JUMP];
        probability_retrig = save_data[SAVE_PROB_RETRIG];
        probability_gate = save_data[SAVE_PROB_GATE];
        probability_tunnel = save_data[SAVE_PROB_TUNNEL];
        const bool clock_mode_was = clock_input_ittybittymidi;
        clock_input_ittybittymidi =
            save_data[SAVE_CLOCK_INPUT_MODE] == CLOCK_INPUT_MIDI;
        save_data[SAVE_CLOCK_INPUT_MODE] =
            clock_input_ittybittymidi ? CLOCK_INPUT_MIDI : CLOCK_INPUT_CLOCK;
        // reset_clock_timing() reinicializa el detector de clock EXTERNO, pero
        // de paso deja btn_reset=true, y el próximo beat onset hace
        // beat_num_total=0 -- o sea manda el loop al slice 0, el inicio de la
        // muestra. Eso era lo que hacía "saltar al inicio" al cargar un estado,
        // incluso con el mismo sample. En un load del usuario solo se
        // reinicializa si el modo de clock realmente cambió (ahí sí hay que
        // resincronizar); si no, el loop sigue donde venía y el recall entra
        // sin corte.
        if (load_is_boot || clock_mode_was != clock_input_ittybittymidi) {
          reset_clock_timing();
        }
#if PIKO_GAMEPI13
        // Posición de los knobs de Function A/B por modo. Sin esto, al bootear
        // la barra de cada modo mostraba el medio (2048) hasta tocarla, porque
        // no hay forma de deducir la posición de knob a partir del parámetro
        // cargado (haría falta la inversa de cada mapeo). El byte mágico evita
        // interpretar un save viejo (ceros en esa zona) como "todo en 0".
        if (save_data[SAVE_KNOB_MAGIC] == SAVE_KNOB_MAGIC_VALUE) {
          for (uint8_t m = 0; m < 8; m++) {
            for (uint8_t k = 0; k < 2; k++) {
              const uint16_t off =
                  (uint16_t)(SAVE_KNOB_BY_MODE + (m * 2 + k) * 2);
              uint16_t v =
                  (uint16_t)(((uint16_t)save_data[off] << 8) | save_data[off + 1]);
              if (v > 4095) v = 4095;
              gamepi_knob_by_mode[m][k] = v;
            }
          }
          gamepi_restore_mode_knobs(gamepi_selector);
          // Timestretch (modo 1, Function B): su parámetro se deriva del knob
          // (set_timestretch_knob), y el knob ya viaja en la tabla de arriba --
          // pero restaurar la tabla NO re-aplica el efecto, así que hasta ahora
          // el stretch se perdía al cargar un estado aunque la barra mostrara
          // el valor correcto. Se re-aplica desde la misma fuente de verdad.
          set_timestretch_knob(gamepi_knob_by_mode[1][1]);
        }
#endif
        sequencer.Load(save_data);
#if PIKO_GAMEPI13
        gamepi_state_loaded_us = time_us_64();
        gamepi_state_in_sync = true;
        gamepi_clear_state_bars();
#endif
#ifdef DEBUG_SAVE
        printf("volume_reduce: %d\n", volume_reduce);
        printf("distortion: %d\n", distortion);
        printf("bpm_set: %d\n", bpm_set);
        printf("filter_fc: %d\n", filter_fc);
        printf("sample_change: %d\n", sample_change);
        printf("noise_gate_thresh: %d\n", noise_gate_thresh);
        printf("probability_direction: %d\n", probability_direction);
        printf("probability_jump: %d\n", probability_jump);
        printf("probability_retrig: %d\n", probability_retrig);
        printf("probability_gate: %d\n", probability_gate);
#endif
      }
    }

    if (clock_ms % 16 == 0) {  // 250 Hz
      // read gpio inputs
      for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
        if (midi_button1 != i && midi_button2 != i) {
          input_button[i].Read();
        }
        // if (input_button[i].ChangedHigh(false)) {
        //   MidiOut_on(midiout, midi_notes[(i % 8)], 127);
        // }
#ifdef DEBUG_BUTTONS
        if (input_button[i].Changed(false)) {
          printf("[%6d] %d: %d", clock_ms, i, input_button[i].On());
          if (input_button[i].Rising()) {
            printf("rising");
          }
          if (input_button[i].Falling()) {
            printf("falling");
          }
          printf("\n");
        }
#endif
      }
      // Capture each button's rising edge ONCE per tick, after all 8 have
      // been read above. Button::ChangedHigh(true) consumes the edge (see
      // doth/button.h) -- the 3 combo checks below used to each call it
      // independently, redundantly re-evaluated once per loop iteration
      // above (harmless there since none of them depend on `i`, but the
      // combos' button-index sets overlap each other: 1 and 6 appear in both
      // the clock-lock and reset-fx combos, 0 and 7 appear in both reset-fx
      // and mute/start-stop), so one consumer could silently eat an edge before
      // another saw it -- the same class of bug already found and fixed for
      // Start earlier this project. Consolidating into one array read here
      // removes both the redundancy and that latent risk, and lets the new
      // Select+musical-button gesture (added in a later task) share the same
      // capture safely.
      bool button_rising[NUM_BUTTONS];
      for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
        button_rising[i] = input_button[i].ChangedHigh(true);
      }
      if (button_rising[1] || button_rising[2] || button_rising[5] ||
          button_rising[6]) {
        if (input_button[1].On() && input_button[2].On() &&
            input_button[5].On() && input_button[6].On()) {
          debounce_lock_clock = 80;
          do_lock_clock = !do_lock_clock;
        }
      }
      if (button_rising[0] || button_rising[1] || button_rising[6] ||
          button_rising[7]) {
        if (input_button[0].On() && input_button[1].On() &&
            input_button[6].On() && input_button[7].On()) {
          // reset fx
          param_set_break(0, filter_fc, distortion, probability_jump,
                          probability_retrig, probability_gate,
                          probability_direction, probability_tunnel,
                          save_data);
        }
      }
      if (button_rising[0] || button_rising[3] || button_rising[4] ||
          button_rising[7]) {
        // button combo
        if (input_button[0].On() && input_button[3].On() &&
            input_button[4].On() && input_button[7].On()) {
          if (do_mute) {
            do_start_everything();
          } else {
            do_stop_everything();
          }
          // printf("switching do mute: %d\n", do_mute);
        }
      }

#if PIKO_GAMEPI13
      // GamePi13: Select cycles the selector; L/R adjust Function A
      // (or Function B while Start is held), with hold-to-repeat.
      btn_select.Read();
      btn_start.Read();
      btn_l.Read();
      btn_r.Read();
      if (btn_select.Changed(true)) {
        if (btn_select.Rising()) {
          gamepi_select_used_as_modifier = false;
        } else if (btn_select.Falling() && !gamepi_select_used_as_modifier) {
          const uint8_t was = gamepi_selector;
          gamepi_selector = (gamepi_selector + 1) % GAMEPI_MODE_COUNT;
          gamepi_switch_mode_knobs(was, gamepi_selector);
          if (was == 8) {
            // Leaving Browse SD: unmount, don't leave the card open, and close
            // whatever SD screen was on-screen -- it's a persistent overlay
            // (see gamepi_ui_sd_close()'s comment), so it won't time out on
            // its own.
            gamepi_sd_unmount_requested = true;
            gamepi_sd_state = GAMEPI_SD_IDLE;
            gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_NONE;
            gamepi_ui_sd_close();
          }
          if (gamepi_selector < 8) {
            input_knob[0].SetBucket(gamepi_selector, 8);
          } else {
            // gamepi_selector == 8: entering Browse SD, kick off the async
            // directory listing.
            gamepi_sd_state = GAMEPI_SD_LISTING;
            gamepi_sd_index = 0;
            gamepi_sd_hold_start_us = 0;
            gamepi_sd_list_done = false;
            __asm volatile("dmb" ::: "memory");
            gamepi_sd_list_requested = true;
            gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_LISTING;
          }
        }
      }
      if (btn_select.On() && !gamepi_select_used_as_modifier) {
        // Hold Select + a musical button to jump directly to that button's
        // mode (0-7) instead of cycling one step at a time. Mirrors Start's
        // own tap-vs-hold-modifier split (see btn_start.Changed(true)
        // further below) -- a plain Select tap (Falling() with the modifier
        // flag still false, handled above) still cycles as before.
        for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
          if (button_rising[i]) {
            const uint8_t was = gamepi_selector;
            if (was == 8) {
              // Leaving Browse SD via a direct jump -- same cleanup the
              // Falling()-cycling path above does, so every way out of
              // mode 8 reliably unmounts the card. A direct jump can only
              // ever land on i < 8, so there's no matching "entering
              // Browse SD" branch needed here.
              gamepi_sd_unmount_requested = true;
              gamepi_sd_state = GAMEPI_SD_IDLE;
              gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_NONE;
              gamepi_ui_sd_close();
            }
            gamepi_selector = i;
            gamepi_switch_mode_knobs(was, gamepi_selector);
            gamepi_select_used_as_modifier = true;
            input_knob[0].SetBucket(gamepi_selector, 8);
            break;  // first musical button pressed this hold wins
          }
        }
      }
      // Consolidated into ONE Changed(true) call: it consumes the button's
      // internal "changed" flag on ANY transition (see doth/button.h --
      // "can only be read once"), so checking Rising() and Falling() via
      // two SEPARATE Changed(true) calls in the same iteration silently
      // drops the second one, whichever it is.
      if (btn_start.Changed(true)) {
        if (btn_start.Rising()) {
          gamepi_start_used_as_modifier = false;
        } else if (btn_start.Falling() && !gamepi_start_used_as_modifier) {
          if (do_mute) {
            do_start_everything();
          } else {
            do_stop_everything();
          }
        }
      }
      if (btn_start.On() && btn_retrig && button_on2 < NUM_BUTTONS) {
        // Continuously (not just the single tick the retrigger's exact-
        // subdivision branch fires in pwm_interrupt_handler) mark Start as
        // "used as a modifier" for as long as a retrigger is active and
        // Start is held -- covers every press ordering (Start before,
        // during, or after the 2-button combo). btn_retrig stays true for
        // the whole effect, not just its first tick, so this reliably wins
        // against Rising()'s reset above regardless of exact timing.
        // Without this, releasing Start shortly after -- but not in the
        // exact same tick as -- the retrigger start could still fall
        // through to the mute/start-stop toggle above.
        // button_on2 < NUM_BUTTONS also requires a REAL second button to be
        // held (set only by the 2-button-combo detection in
        // pwm_interrupt_handler) -- btn_retrig alone isn't enough, since it
        // can also become true purely from probability_retrig's random
        // per-beat roll (see "check button 2" -> the probability branch)
        // with no button combo involved at all. Without this extra check,
        // high "break fx" intensity (which raises probability_retrig) made
        // btn_retrig true almost continuously, so pressing Start to stop
        // playback very often got misread as "Start held as a combo
        // modifier" and silently swallowed the stop -- confirmed on
        // hardware: with break fx at max, Start stopped responding until
        // the intensity was lowered back down.
        gamepi_start_used_as_modifier = true;
      }
      if (gamepi_selector < 8) {
        const uint8_t active_knob = btn_start.On() ? 2 : 1;
        const uint64_t now_repeat_us = time_us_64();
        // Tempo (mode 7 / Volumen, Function B) gets a dedicated direct
        // bpm_set adjustment instead of the generic raw-knob Adjust() path:
        // BPM has a much wider practical range (20-360) than the 0-4095
        // knobs the generic path was designed for, so a flat GAMEPI_KNOB_STEP
        // translated into huge BPM swings per repeat. This mirrors a
        // tap/hold-1s/hold-3s acceleration (1/5/20 BPM per repeat) instead.
        const bool is_tempo = (gamepi_selector == 7 && active_knob == 2);
        // Selección de sample (modo 0, Function A) tiene el mismo problema que
        // tuvo Tempo: el paso genérico de knob (GAMEPI_KNOB_STEP=164 de 4095)
        // es mucho más chico que el "casillero" de cada sample cuando el
        // banco tiene pocas muestras, así que un solo toque casi nunca
        // alcanza a cruzar al siguiente. Mismo mecanismo que is_tempo: evita
        // Adjust() y escribe sample_change directamente, ±1 por
        // toque/repetición, sin acelerar, con clamp en los extremos (sin dar
        // la vuelta) -- ver docs/superpowers/specs/2026-07-19-sample-select-direct-step-design.md.
        const bool is_sample_select = (gamepi_selector == 0 && active_knob == 1);
        if (btn_l.On()) {
          if (is_tempo && gamepi_tempo_hold_l_us == 0) {
            gamepi_tempo_hold_l_us = now_repeat_us;
          }
          if (now_repeat_us >= gamepi_next_repeat_l_us) {
            if (is_tempo) {
              const uint64_t held_us = now_repeat_us - gamepi_tempo_hold_l_us;
              const uint16_t step =
                  held_us >= GAMEPI_TEMPO_TIER3_US ? GAMEPI_TEMPO_STEP_FAST
                  : held_us >= GAMEPI_TEMPO_TIER2_US ? GAMEPI_TEMPO_STEP_MED
                                                     : GAMEPI_TEMPO_STEP_FINE;
              uint16_t new_bpm = bpm_set > (uint16_t)(GAMEPI_TEMPO_MIN_BPM + step)
                                      ? (uint16_t)(bpm_set - step)
                                      : GAMEPI_TEMPO_MIN_BPM;
              param_set_bpm(new_bpm, bpm_set, beat_thresh, audio_clk_thresh);
              gamepi_start_used_as_modifier = true;
            } else if (is_sample_select) {
              const uint16_t sample_count = (uint16_t)piko_audio_sample_count();
              if (sample_count > 0 && sample_change > 0) {
                sample_change--;
                save_data[SAVE_SAMPLE] = sample_change;
              }
            } else {
              // Modo 6: la barra se vacía al concretarse la acción; si el
              // botón sigue apretado, el auto-repeat la rellenaría y volvería a
              // disparar la escritura. Ver gamepi_state_bar_latched.
              if (!(gamepi_selector == 6 && gamepi_state_bar_latched)) {
                input_knob[active_knob].Adjust(-GAMEPI_KNOB_STEP);
              }
              if (active_knob == 2) gamepi_start_used_as_modifier = true;
            }
            // Cualquier ajuste de parámetro deja memoria y flash desfasados.
            // El modo 6 se excluye: sus barras son el control de save/load, no
            // un parámetro del estado.
            if (gamepi_selector != 6) gamepi_state_in_sync = false;
            if (gamepi_repeat_count_l < 2) gamepi_repeat_count_l++;
            const uint64_t next_interval_l =
                (gamepi_repeat_count_l == 1) ? GAMEPI_FIRST_REPEAT_US
                                             : GAMEPI_REPEAT_US;
            gamepi_next_repeat_l_us = now_repeat_us + next_interval_l;
          }
        } else {
          gamepi_next_repeat_l_us = 0;
          gamepi_tempo_hold_l_us = 0;
          gamepi_repeat_count_l = 0;
          gamepi_state_bar_latched = false;
        }
        if (btn_r.On()) {
          if (is_tempo && gamepi_tempo_hold_r_us == 0) {
            gamepi_tempo_hold_r_us = now_repeat_us;
          }
          if (now_repeat_us >= gamepi_next_repeat_r_us) {
            if (is_tempo) {
              const uint64_t held_us = now_repeat_us - gamepi_tempo_hold_r_us;
              const uint16_t step =
                  held_us >= GAMEPI_TEMPO_TIER3_US ? GAMEPI_TEMPO_STEP_FAST
                  : held_us >= GAMEPI_TEMPO_TIER2_US ? GAMEPI_TEMPO_STEP_MED
                                                     : GAMEPI_TEMPO_STEP_FINE;
              uint16_t new_bpm = (uint16_t)(bpm_set + step);
              if (new_bpm > GAMEPI_TEMPO_MAX_BPM) new_bpm = GAMEPI_TEMPO_MAX_BPM;
              param_set_bpm(new_bpm, bpm_set, beat_thresh, audio_clk_thresh);
              gamepi_start_used_as_modifier = true;
            } else if (is_sample_select) {
              const uint16_t sample_count = (uint16_t)piko_audio_sample_count();
              if (sample_count > 0 && sample_change < sample_count - 1) {
                sample_change++;
                save_data[SAVE_SAMPLE] = sample_change;
              }
            } else {
              // Modo 6: la barra se vacía al concretarse la acción; si el
              // botón sigue apretado, el auto-repeat la rellenaría y volvería a
              // disparar la escritura. Ver gamepi_state_bar_latched.
              if (!(gamepi_selector == 6 && gamepi_state_bar_latched)) {
                input_knob[active_knob].Adjust(GAMEPI_KNOB_STEP);
              }
              if (active_knob == 2) gamepi_start_used_as_modifier = true;
            }
            if (gamepi_selector != 6) gamepi_state_in_sync = false;
            if (gamepi_repeat_count_r < 2) gamepi_repeat_count_r++;
            const uint64_t next_interval_r =
                (gamepi_repeat_count_r == 1) ? GAMEPI_FIRST_REPEAT_US
                                             : GAMEPI_REPEAT_US;
            gamepi_next_repeat_r_us = now_repeat_us + next_interval_r;
          }
        } else {
          gamepi_next_repeat_r_us = 0;
          gamepi_tempo_hold_r_us = 0;
          gamepi_repeat_count_r = 0;
          gamepi_state_bar_latched = false;
        }
      }

      if (gamepi_selector == 8) {
        switch (gamepi_sd_state) {
          case GAMEPI_SD_IDLE:
            break;
          case GAMEPI_SD_LISTING:
            if (gamepi_sd_list_done) {
              if (gamepi_sd_file_count() == 0) {
                strncpy(gamepi_sd_redraw_error_msg, "No card or files",
                       sizeof(gamepi_sd_redraw_error_msg) - 1);
                gamepi_sd_redraw_error_msg[sizeof(gamepi_sd_redraw_error_msg) - 1] = '\0';
                gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_ERROR;
                gamepi_sd_state = GAMEPI_SD_IDLE;
              } else {
                gamepi_sd_index = 0;
                gamepi_sd_state = GAMEPI_SD_BROWSE;
                gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_BROWSE;
              }
            }
            break;
          case GAMEPI_SD_BROWSE: {
            // L cycles the list (one direction, wraps -- reaches every file
            // eventually). R is dedicated purely to hold-to-confirm: it used
            // to also tap-navigate forward, but rapid taps could leave the
            // button reading "on" across what looked like separate presses
            // (debounce/bounce), letting the hold timer accumulate real
            // elapsed time across several taps and cross the 1s threshold
            // without ever being held once -- an unintended load. Splitting
            // navigate (L only) from confirm (R only) removes that failure
            // mode entirely.
            const uint32_t count = gamepi_sd_file_count();
            bool moved = false;
            if (btn_l.ChangedHigh(true) && btn_l.On() && count > 0) {
              gamepi_sd_index = (gamepi_sd_index + count - 1) % count;
              moved = true;
            }
            if (moved) {
              gamepi_sd_hold_start_us = 0;
              gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_BROWSE;
            }
            if (btn_r.On()) {
              const uint64_t now_us = time_us_64();
              if (gamepi_sd_hold_start_us == 0) {
                gamepi_sd_hold_start_us = now_us;
              } else {
                const uint64_t held_us = now_us - gamepi_sd_hold_start_us;
                if (held_us < GAMEPI_SD_HOLD_CONFIRM_US) {
                  const uint8_t pct = (uint8_t)(
                      (held_us * 100u) / GAMEPI_SD_HOLD_CONFIRM_US);
                  gamepi_ui_sd_confirm_progress(
                      gamepi_sd_file_name(gamepi_sd_index), pct);
                } else {
                  gamepi_sd_load_index = gamepi_sd_index;
                  gamepi_sd_load_done = false;
                  __asm volatile("dmb" ::: "memory");
                  gamepi_sd_load_requested = true;
                  gamepi_sd_state = GAMEPI_SD_LOADING;
                  gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_LOADING;
                }
              }
            } else {
              if (gamepi_sd_hold_start_us != 0) {
                // Was mid-hold (showing the confirm-progress overlay) and
                // got released before reaching the threshold -- restore the
                // browse screen. SD overlays are persistent now (no
                // auto-expiry), so without this the "Cargando... XX%"
                // screen would stay frozen on-screen indefinitely.
                gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_BROWSE;
              }
              gamepi_sd_hold_start_us = 0;
            }
            break;
          }
          case GAMEPI_SD_LOADING:
            if (gamepi_sd_load_done) {
              if (gamepi_sd_load_ok) {
                // Safe to read gamepi_sd_file_name() here: core1 already
                // guaranteed (via its dmb-then-gamepi_sd_load_done protocol)
                // that sd_file_names[] is fully settled by the time this
                // flag is observed true, and it won't be touched again until
                // the next sd_list_files() call. Copy it into a core0-owned
                // buffer so it survives past that point (and past any future
                // re-listing), for the dashboard/browse-list indicator.
                const char *loaded_name = gamepi_sd_file_name(gamepi_sd_load_index);
                strncpy(gamepi_active_bank_name, loaded_name,
                       sizeof(gamepi_active_bank_name) - 1);
                gamepi_active_bank_name[sizeof(gamepi_active_bank_name) - 1] = '\0';
              }
              gamepi_sd_result_deadline_us = time_us_64() + GAMEPI_SD_RESULT_US;
              gamepi_sd_state = GAMEPI_SD_RESULT;
              gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_RESULT;
            }
            break;
          case GAMEPI_SD_RESULT:
            if (time_us_64() < gamepi_sd_result_deadline_us) {
              // still showing "Listo"/"Error"
            } else {
              gamepi_sd_state = GAMEPI_SD_BROWSE;
              gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_BROWSE;
            }
            break;
        }
      }
#endif

#if PIKO_GAMEPI13
      // Boot-time bank rescan retry. Confirmed on this board: the very first
      // rescan at boot deterministically reads a phantom empty header, while
      // later reads of the same flash address return the real bank (see
      // PikoAudioBank.cpp / commit history). Until the underlying early-XIP
      // read issue is understood, retry once per second while the bank looks
      // empty; on success rebind sample timing so playback starts. The LCD's
      // top-right sample counter doubles as the diagnostic: it flips from
      // "--/--" to "NN/MM" the moment a rescan finally reads the real header.
      if (piko_audio_sample_count() == 0 && !piko_audio_bank_mutating()) {
        static uint64_t gamepi_next_rescan_us = 0;
        const uint64_t now_us = time_us_64();
        if (now_us >= gamepi_next_rescan_us) {
          gamepi_next_rescan_us = now_us + 1000000ull;
          piko_audio_bank_set_mutating(true);
          piko_audio_bank_rescan();
          piko_audio_bank_set_mutating(false);
          if (piko_audio_sample_count() > 0) {
            refresh_sample_timing(0);
          }
        }
      }
      // Corre ANTES de gamepi_ui_tick(): su camino normal (overlay_on falso)
      // llama a flush_allowed() sin condición cada tick, así que si este
      // bloque corriera después, gamepi_ui_tick() siempre "ganaría" el
      // próximo turno disponible primero -- una vez que se sale del modo 8
      // (overlay_on vuelve a falso), eso deja a este bloque sin ninguna
      // oportunidad real de volver a dibujar nunca más. Puesto primero, el
      // reintento del modo 8 tiene prioridad; el dashboard normal tolera
      // ceder un tick (ya se reintenta solo en su propio próximo llamado).
      if (gamepi_sd_redraw_kind != GAMEPI_SD_REDRAW_NONE) {
        bool ok = false;
        switch (gamepi_sd_redraw_kind) {
          case GAMEPI_SD_REDRAW_LISTING:
            ok = gamepi_ui_sd_listing();
            break;
          case GAMEPI_SD_REDRAW_BROWSE: {
            const uint32_t count = gamepi_sd_file_count();
            const bool is_active = count > 0 && gamepi_active_bank_name[0] != '\0' &&
                strcmp(gamepi_sd_file_name(gamepi_sd_index), gamepi_active_bank_name) == 0;
            ok = count > 0 && gamepi_ui_sd_browse(gamepi_sd_file_name(gamepi_sd_index),
                                                  gamepi_sd_index, count, is_active);
            break;
          }
          case GAMEPI_SD_REDRAW_LOADING:
            ok = gamepi_ui_sd_loading(gamepi_sd_file_name(gamepi_sd_load_index));
            break;
          case GAMEPI_SD_REDRAW_RESULT:
            ok = gamepi_ui_sd_result(gamepi_sd_load_ok,
                                     gamepi_sd_file_name(gamepi_sd_load_index));
            break;
          case GAMEPI_SD_REDRAW_ERROR:
            ok = gamepi_ui_sd_error(gamepi_sd_redraw_error_msg);
            break;
          default:
            break;
        }
        if (ok) gamepi_sd_redraw_kind = GAMEPI_SD_REDRAW_NONE;
      }
      {
        GamepiUiState uis;
        uis.bpm = bpm_set;
        uis.clock_src =
            clock_input_ittybittymidi ? 2 : ((is_syncing && do_sync_play) ? 1 : 0);
        uint16_t ui_scount = (uint16_t)piko_audio_sample_count();
        uis.sample_count = ui_scount;
        // sample_change (no sample_set) para que el dashboard refleje la
        // selección al instante -- sample_set solo se sincroniza desde
        // sample_change en un evento de compás dentro de la ISR de audio
        // (pwm_interrupt_handler), que nunca ocurre mientras el reproductor
        // está detenido (do_mute), dejando el display congelado hasta que
        // vuelve a sonar. sample_change ya está siempre acotado a un rango
        // válido por todos los puntos donde se escribe.
        uis.sample_idx = ui_scount ? (uint16_t)(sample_change % ui_scount) : 0;
        if (ui_scount > 0) {
          const char *nm = piko_audio_sample(uis.sample_idx).name;
          size_t n = 0;
          while (n < sizeof(uis.sample_name) - 1 && n < 48 && nm[n] != '\0') {
            uis.sample_name[n] = nm[n];
            n++;
          }
          uis.sample_name[n] = '\0';
        } else {
          snprintf(uis.sample_name, sizeof(uis.sample_name), "(no samples)");
        }
        for (uint8_t j = 0; j < 8; j++) uis.leds[j] = ledarray.Get(j);
        uis.retrig_leds_mask = 0;
        if (btn_retrig) {
          if (button_on < NUM_BUTTONS) {
            uis.retrig_leds_mask |= (uint8_t)(1u << button_on);
          }
          if (button_on2 < NUM_BUTTONS) {
            uis.retrig_leds_mask |= (uint8_t)(1u << button_on2);
          }
        }
        {
          // Playing sample (`sample`, ISR-owned; may differ from sample_set
          // while the tunnel FX hops) + playhead column against ITS length,
          // so the cursor always matches what's audible.
          const uint16_t playing = sample;
          uis.wave_sample_idx = playing;
          const uint32_t wave_len = raw_len(playing);
          if (ui_scount > 0 && wave_len > 1) {
            const uint32_t ph = phase_sample[phase_head] % wave_len;
            uis.wave_playhead_col = (uint8_t)(((uint64_t)ph * 240u) / wave_len);
          } else {
            uis.wave_playhead_col = 255;  // no playhead
          }
        }
        uis.mode = gamepi_selector;
        strncpy(uis.active_bank_name, gamepi_active_bank_name,
               sizeof(uis.active_bank_name) - 1);
        uis.active_bank_name[sizeof(uis.active_bank_name) - 1] = '\0';
        uis.knob_a = input_knob[1].Value();
        uis.knob_b = input_knob[2].Value();
        {
          // Ambos íconos reflejan el MISMO hecho: memoria y flash coinciden.
          // Encendidos tras guardar o cargar, apagados en cuanto se toca un
          // parámetro. Ver gamepi_state_in_sync para por qué es un estado
          // permanente y no un flash temporal.
          uis.state_saved = gamepi_state_in_sync;
          uis.state_loaded = gamepi_state_in_sync;
        }
        uis.seq_len = sequencer.Len();
        uis.seq_step = sequencer.NextI(beat_num_total);
        uis.seq_recording = sequencer.IsRecording();
        uis.seq_playing = sequencer.IsPlaying();
        uis.playing = !do_mute;
        gamepi_ui_tick(uis);
      }
#endif

      // adc reading
      if (!btn_retrig) {
        for (uint8_t i = 0; i < NUM_KNOBS; i++) {
          input_knob[i].Read();

          // set the current midi note if a button is held down
          if (input_knob[i].Changed() && i == 0) {
            // midi_notes_set
            for (uint8_t j = 0; j < NUM_BUTTONS; j++) {
              if (input_button[j].On()) {
                midi_notes_set[j] =
                    midi_notes_available[input_knob[i].Value() *
                                         MIDI_NOTES_AVAILABLE_TOTAL / 4095];
              }
            }
          }

          if (input_knob[i].Changed() || first_time) {
            if (i == 0) {
              uint8_t selector_knob_before = selector_knob;
              selector_knob =
                  (input_knob[i].Value() * 8 / input_knob[i].ValueMax());
#ifdef DEBUG_KNOB
              printf("%d: %d; \n", i, input_knob[i].Value());
#endif
              if (selector_knob != selector_knob_before) {
                has_saved = false;
                for (uint8_t j = 1; j < NUM_KNOBS; j++) {
                  input_knob[j].Reset();  // prevent spurious changes when
                                          // changing selection
                }
              }
              ledarray_sel = selector_knob;
              ledarray_sel_debounce = 16000;
              sequencer.SetRecording(false);
              if (first_time) {
                first_time = false;
                break;
              }
            } else if (i == 1) {
              ledarray_sel_debounce = 0;
#ifdef DEBUG_KNOB
              printf("%d: %d; \n", i, input_knob[i].Value());
#endif
              /////////////
              // KNOB A //
              ////////////
              switch (selector_knob) {
                case 0:
                  // sample
                  if (debounce_sample == 0 && piko_audio_sample_count() > 0) {
                    uint16_t sample_count = piko_audio_sample_count();
                    sample_change = input_knob[i].Value() * sample_count /
                                    input_knob[i].ValueMax();
                    if (sample_change >= sample_count) {
                      sample_change = sample_count - 1;
                    }
                    debounce_sample = 500;
                    save_data[SAVE_SAMPLE] = sample_change;
                  }
                  break;
                case 1:
                  filter_fc = input_knob[i].Value() * (LPF_MAX + 10) /
                              input_knob[i].ValueMax();
                  save_data[SAVE_FILTER] = filter_fc;
                  break;
                case 2:
                  // gate
                  if (input_knob[i].Value() > 3700) {
                    noise_gate_thresh = gate_default_thresh();
                  } else {
                    noise_gate_thresh =
                        gate_scaled_thresh(input_knob[i].Value(),
                                           input_knob[i].ValueMax());
                  }
                  save_data[SAVE_GATE] = (uint8_t)(noise_gate_thresh >> 8);
                  save_data[SAVE_GATE + 1] = (uint8_t)noise_gate_thresh;
                  break;
                case 3:
                  // jump probability
                  if (input_knob[i].Value() < 200) {
                    probability_jump = 0;
                  } else {
                    probability_jump = (input_knob[i].Value() * 254 /
                                        input_knob[i].ValueMax());
                  }
                  save_data[SAVE_PROB_JUMP] = probability_jump;
                  break;
                case 4:
                  // tunnel probability
                  if (input_knob[i].Value() < 200) {
                    probability_tunnel = 0;
                  } else {
                    probability_tunnel = (input_knob[i].Value() * 254 /
                                          input_knob[i].ValueMax());
                  }
                  save_data[SAVE_PROB_TUNNEL] = probability_tunnel;
                  break;
                case 5:
                  // sequencer rec
                  if (input_knob[i].Value() > 3500) {
                    sequencer.SetRecording(true);
                  } else {
                    sequencer.SetRecording(false);
                    if (input_knob[i].Value() < 1000) {
                      sequencer.Reset();
                    }
                  }
                  break;
                case 6:
                  // save
                  if (input_knob[i].Value() > 2040) {
                    if (!has_saved) {
                      has_saved = true;
                      debounce_saving = 32000;
                      debounce_led_save = 255;
                    }
                  } else {
                    has_saved = false;
                  }
                  break;
                case 7:
                  // volume
                  save_data[SAVE_VOLUME] =
                      (uint8_t)(input_knob[i].Value() >> 8);
                  save_data[SAVE_VOLUME + 1] = (uint8_t)input_knob[i].Value();
                  param_set_volume(input_knob[i].Value(), distortion,
                                   volume_reduce);
#ifdef DEBUG_KNOB
                  printf("%d: %d; \n", i, input_knob[i].Value());
#endif
                  break;
                default:
                  break;
              }
            } else if (i == 2) {
              ledarray_sel_debounce = 0;
#ifdef DEBUG_KNOB
              printf("%d: %d; \n", i, input_knob[i].Value());
              printf("[%d] %d: %d; \n", selector_knob, i,
                     input_knob[i].Value());
#endif

              switch (selector_knob) {
                case 0:
                  param_set_break(input_knob[i].Value(), filter_fc, distortion,
                                  probability_jump, probability_retrig,
                                  probability_gate, probability_direction,
                                  probability_tunnel, save_data);
                  break;
                case 1:
                  // stretch
                  set_timestretch_knob(input_knob[i].Value());
                  break;
                case 2:
                  // gate probability
                  if (input_knob[i].Value() < 200) {
                    probability_gate = 0;
                  } else {
                    probability_gate = (input_knob[i].Value() * 254 /
                                        input_knob[i].ValueMax());
                  }
                  save_data[SAVE_PROB_GATE] = probability_gate;
                  break;
                case 3:
                  // retrig probability
                  if (input_knob[i].Value() < 200) {
                    probability_retrig = 0;
                  } else {
                    probability_retrig = (input_knob[i].Value() * 254 /
                                          input_knob[i].ValueMax());
                  }
                  save_data[SAVE_PROB_RETRIG] = probability_retrig;
                  break;
                case 4:
                  // reverse probability
                  if (input_knob[i].Value() < 200) {
                    probability_direction = 0;
                  } else {
                    probability_direction = (input_knob[i].Value() * 254 /
                                             input_knob[i].ValueMax());
                  }
                  save_data[SAVE_PROB_DIRECTION] = probability_direction;
                  break;
                case 5:
                  // sequencer on
                  sequencer.SetPlaying(input_knob[i].Value() > 2200);
                  if (sequencer.IsPlaying()) {
                    debounce_led_sequencer = 255;
                  }
                  break;
                case 6:
                  // load
                  if (input_knob[i].Value() > 4000 && !has_loaded) {
                    do_load = true;
                    load_is_boot = false;
                    debounce_led_load = 255;
                    has_loaded = true;
                  } else {
                    has_loaded = false;
                  }

                  break;
                case 7:
                  // tempo
                  if (clock_sync_ms > 60000) {
                    uint16_t bpm_set_new = round((double)input_knob[i].Value() *
                                                 255.0 / 4095 / 5) *
                                               5 +
                                           50;
                    ledarray_binary_debounce = 48000;
                    ledarray_binary = bpm_set_new - 50;
                    if (bpm_set_new > 360) {
                      bpm_set_new = 360;
                    }
                    if (bpm_set_new != bpm_set) {
#ifdef DEBUG_KNOB
                      printf("%d: %d; \n", i, input_knob[i].Value());
#endif
                      save_data[SAVE_BPM] = (uint8_t)(bpm_set_new >> 8);
                      save_data[SAVE_BPM + 1] = (uint8_t)bpm_set_new;

                      param_set_bpm(bpm_set_new, bpm_set, beat_thresh,
                                    audio_clk_thresh);
                    }
                  }
                  break;

                default:
                  break;
              }
            }
          }
        }
      }
      // adc reading end
    }

    if (!clock_input_ittybittymidi) {
      // trigger in
      uint8_t clock_pin = 1 - gpio_get(CLOCK_PIN);
      // code to verify polarity -KEEP
      // if (clock_pin == 1 && clock_pin_last == 0) {
      //   printf("[%d] on\n", clock_sync_ms);
      //   clock_sync_ms = 0;
      // }
      // if (clock_pin == 0 && clock_pin_last == 1) {
      //   printf("[%d] off\n", clock_sync_ms);
      //   clock_sync_ms = 0;
      // }
      if (clock_pin == 1 && clock_pin_last == 0) {
#ifdef DEBUG_CALIBRATE_PO
        // this is used for calibration
        printf("%d\n", clock_sync_ms);
#endif
        if (syncing_clicks < 10) {
          syncing_clicks++;
          is_syncing = true;
        }
        do_sync_play = true;
        // this is from a calibration
        if (clock_sync_ms > 10000) {
          // out of range of the bpm, but will use to reset system
          btn_reset = true;
          clock_hits = 0;
        } else {
          bpm_input = 512508000 / ((935 * clock_sync_ms + 31900));
          ra.Update(bpm_input);
          bpm_input = ra.Value();
          if (bpm_input != bpm_set) {
#ifdef DEBUG_CLOCK
            printf("%d, %d\n", clock_sync_ms, bpm_input);
#endif
            // REDUCE THE BPM INPUT TO ELIMINATE OVERSTEPPING
            param_set_bpm(bpm_input - 7, bpm_set, beat_thresh,
                          audio_clk_thresh);
          }
          clock_hits++;
          soft_sync = true;  // TEST
          if (clock_hits % 16 == 0) {
            soft_sync = true;
          }
        }
        clock_sync_ms = 0;
      }
      if (is_syncing && clock_sync_ms > 10000) {
        do_sync_play = false;
      }
      clock_pin_last = clock_pin;
    }

    // trig out
    output_trigger.Update();

    if (ledarray_binary_debounce > 0) {
      ledarray_binary_debounce--;
      ledarray.SetBinary(ledarray_binary);
    } else if (sequencer.IsRecording()) {
      ledarray.Clear();
      if (sequencer.Last() < 255) {
        ledarray.Set(sequencer.Last() % NUM_BUTTONS, 10000);
      }
    } else {
      ledarray.Clear();
      if (ledarray_sel_debounce > 0) {
        ledarray_sel_debounce--;
        ledarray.Set(ledarray_sel, 950);
      } else {
        if (button_on < NUM_BUTTONS) {
          ledarray.Add(button_on, 250);
          if (button_on2 < NUM_BUTTONS) {
            ledarray.Add(button_on2, 250);
          }
        } else {
          ledarray.Add(select_beat % NUM_BUTTONS, 250);
        }
      }
    }
    ledarray.Update();

    // sleep this thread
    sleep_us(MAIN_LOOP_DELAY);
  }
}
