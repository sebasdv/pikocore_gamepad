// Host check for doth/usb_midi_in.h: the USB-MIDI queue and dispatch.
// Run with tests/firmware/run_checks.bat.
#include <assert.h>
#include <stddef.h>
#include <stdint.h>

#define PIKO_DMB() ((void)0)  // single-threaded here; the firmware uses dmb
#include "usb_midi_in.h"

enum { EV_NONE, EV_NOTE_ON, EV_NOTE_OFF, EV_START, EV_CONT, EV_STOP, EV_TIMING };
static struct { int kind; uint8_t note, vel; int count; } ev;

static void rec(int kind) { ev.kind = kind; ev.count++; }
static void rec_note_on(uint8_t note, uint8_t vel) { ev.note = note; ev.vel = vel; rec(EV_NOTE_ON); }
static void rec_note_off(uint8_t note) { ev.note = note; rec(EV_NOTE_OFF); }
static void rec_start(void) { rec(EV_START); }
static void rec_cont(void) { rec(EV_CONT); }
static void rec_stop(void) { rec(EV_STOP); }
static void rec_timing(void) { rec(EV_TIMING); }

static const UsbMidiInCallbacks cb = {rec_note_on, rec_note_off, rec_start,
                                      rec_cont, rec_stop, rec_timing};

static void dispatch_one(const uint8_t p[4]) { usb_midi_in_dispatch(p, &cb); }

static void reset(void) {
  uint8_t out[4];
  while (usb_midi_in_pop(out)) {}
  usb_midi_in_dropped = 0;
}

static void test_realtime(void) {
  uint8_t p[4] = {0x0F, 0xF8, 0, 0};      dispatch_one(p); assert(ev.kind == EV_TIMING);
  p[1] = 0xFA;                            dispatch_one(p); assert(ev.kind == EV_START);
  p[1] = 0xFB;                            dispatch_one(p); assert(ev.kind == EV_CONT);
  p[1] = 0xFC;                            dispatch_one(p); assert(ev.kind == EV_STOP);
}

static void test_notes(void) {
  uint8_t on[4]  = {0x09, 0x93, 60, 100}; dispatch_one(on);
  assert(ev.kind == EV_NOTE_ON && ev.note == 60 && ev.vel == 100);
  uint8_t on0[4] = {0x09, 0x90, 61, 0};   dispatch_one(on0);
  assert(ev.kind == EV_NOTE_OFF && ev.note == 61);
  uint8_t off[4] = {0x08, 0x8F, 62, 64};  dispatch_one(off);
  assert(ev.kind == EV_NOTE_OFF && ev.note == 62);
}

static void test_ignored_messages(void) {
  const uint8_t ignored[][4] = {
    {0x04, 0xF0, 0x7D, 0x01}, {0x07, 0x02, 0x03, 0xF7},   // sysex
    {0x0B, 0xB0, 7, 100}, {0x0E, 0xE0, 0, 64},            // CC, pitch bend
    {0x0F, 0xFE, 0, 0}, {0x0C, 0xC0, 5, 0},               // active sensing, program
  };
  ev.count = 0;
  for (size_t i = 0; i < sizeof ignored / sizeof ignored[0]; i++) dispatch_one(ignored[i]);
  assert(ev.count == 0);
  uint8_t cable1[4] = {0x19, 0x90, 64, 1}; dispatch_one(cable1);   // cable 1: still counts
  assert(ev.kind == EV_NOTE_ON && ev.note == 64);
}

static void test_null_callbacks_are_skipped(void) {
  UsbMidiInCallbacks only_clock = {0};
  only_clock.timing = rec_timing;
  uint8_t on[4] = {0x09, 0x90, 60, 100};
  ev.count = 0; usb_midi_in_dispatch(on, &only_clock); assert(ev.count == 0);
}

static void test_queue_order_and_service(void) {
  reset();
  uint8_t a[4] = {0x0F, 0xFA, 0, 0}, b[4] = {0x0F, 0xF8, 0, 0};
  assert(usb_midi_in_push(a) && usb_midi_in_push(b));
  ev.count = 0; usb_midi_in_service(&cb);
  assert(ev.count == 2 && ev.kind == EV_TIMING);          // a first, b last
  uint8_t out[4]; assert(!usb_midi_in_pop(out));          // empty
}

static void test_full_queue_drops_newest(void) {
  reset();
  uint8_t p[4] = {0x09, 0x90, 0, 1};
  for (int i = 0; i < USB_MIDI_IN_QUEUE_LEN; i++) { p[2] = (uint8_t)i; assert(usb_midi_in_push(p)); }
  p[2] = 99; assert(!usb_midi_in_push(p)); assert(usb_midi_in_dropped == 1);
  uint8_t out[4];
  for (int i = 0; i < USB_MIDI_IN_QUEUE_LEN; i++) { assert(usb_midi_in_pop(out)); assert(out[2] == i); }
  assert(!usb_midi_in_pop(out));
}

static void test_indices_wrap(void) {
  reset();
  uint8_t p[4] = {0x09, 0x90, 0, 1}, out[4];
  for (int i = 0; i < 300; i++) {
    p[2] = (uint8_t)(i & 0x7F); assert(usb_midi_in_push(p));
    assert(usb_midi_in_pop(out)); assert(out[2] == (uint8_t)(i & 0x7F));
    assert(!usb_midi_in_pop(out));
  }
  assert(usb_midi_in_dropped == 0);
}

int main(void) {
  test_realtime();
  test_notes();
  test_ignored_messages();
  test_null_callbacks_are_skipped();
  test_queue_order_and_service();
  test_full_queue_drops_newest();
  test_indices_wrap();
  return 0;
}
