// MIDI IN over USB: clock, transport and notes from a computer or phone.
//
// The USB stack runs on core 1 (tud_task() in piko_sample_manager_core), but
// the callbacks below touch sequencer state that belongs to core 0's control
// loop. So core 1 only queues the USB-MIDI event packets and core 0 drains
// and dispatches them, in the same loop and to the same callbacks the
// one-wire receiver (onewiremidi.h) uses:
//
//   core 1: tud_midi_rx_cb -> usb_midi_in_push     (the only producer)
//   core 0: usb_midi_in_service -> pop -> dispatch (the only consumer)
//
// Single producer, single consumer: free-running uint8_t counters (256 is a
// multiple of the queue length) and a barrier on each side, no locks. A full
// queue drops the newest packet and counts it.
#ifndef USB_MIDI_IN_LIB
#define USB_MIDI_IN_LIB 1

#include <stdbool.h>
#include <stdint.h>
#ifdef DEBUG_MIDI
#include <stdio.h>
#endif
#ifndef PIKO_DMB
#include "../src/piko_barrier.h"
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define USB_MIDI_IN_QUEUE_LEN 64

// Same order as the callbacks Onewiremidi_new() takes. NULL = ignored.
typedef struct UsbMidiInCallbacks {
  void (*note_on)(uint8_t note, uint8_t velocity);
  void (*note_off)(uint8_t note);
  void (*start)(void);
  void (*cont)(void);
  void (*stop)(void);
  void (*timing)(void);
} UsbMidiInCallbacks;

static uint8_t usb_midi_in_buf[USB_MIDI_IN_QUEUE_LEN][4];
static volatile uint8_t usb_midi_in_head;  // written by core 1 only
static volatile uint8_t usb_midi_in_tail;  // written by core 0 only
static volatile uint32_t usb_midi_in_dropped;

// Core 1. false = queue full, packet dropped and counted.
static inline bool usb_midi_in_push(const uint8_t packet[4]) {
  const uint8_t head = usb_midi_in_head;
  if ((uint8_t)(head - usb_midi_in_tail) >= USB_MIDI_IN_QUEUE_LEN) {
    usb_midi_in_dropped++;
    return false;
  }
  uint8_t *slot = usb_midi_in_buf[head & (USB_MIDI_IN_QUEUE_LEN - 1)];
  for (int i = 0; i < 4; i++) slot[i] = packet[i];
  PIKO_DMB();  // the slot is written before core 0 can see the new head
  usb_midi_in_head = (uint8_t)(head + 1u);
  return true;
}

// Core 0. false = queue empty.
static inline bool usb_midi_in_pop(uint8_t packet[4]) {
  const uint8_t tail = usb_midi_in_tail;
  if (tail == usb_midi_in_head) return false;
  PIKO_DMB();  // read the slot only after seeing the head that published it
  const uint8_t *slot = usb_midi_in_buf[tail & (USB_MIDI_IN_QUEUE_LEN - 1)];
  for (int i = 0; i < 4; i++) packet[i] = slot[i];
  PIKO_DMB();  // done reading before core 1 may reuse the slot
  usb_midi_in_tail = (uint8_t)(tail + 1u);
  return true;
}

// One USB-MIDI event packet: packet[0] is cable/CIN (ignored), packet[1] the
// status byte. Clock and transport, and note on/off (velocity 0 = off);
// everything else (sysex, CC, sensing...) is dropped.
static inline void usb_midi_in_dispatch(const uint8_t packet[4],
                                        const UsbMidiInCallbacks *cb) {
  const uint8_t status = packet[1];
  if (status >= 0xF8) {
    void (*f)(void) = status == 0xF8   ? cb->timing
                      : status == 0xFA ? cb->start
                      : status == 0xFB ? cb->cont
                      : status == 0xFC ? cb->stop
                                       : NULL;
    if (f) f();
    return;
  }
  const uint8_t kind = status & 0xF0;
  if (kind == 0x90 && packet[3] > 0) {
    if (cb->note_on) cb->note_on(packet[2], packet[3]);
  } else if (kind == 0x90 || kind == 0x80) {
    if (cb->note_off) cb->note_off(packet[2]);
  }
}

// Core 0, once per control-loop pass: everything queued so far.
static inline void usb_midi_in_service(const UsbMidiInCallbacks *cb) {
  uint8_t packet[4];
  while (usb_midi_in_pop(packet)) usb_midi_in_dispatch(packet, cb);
#ifdef DEBUG_MIDI
  static uint32_t reported = 0;
  if (usb_midi_in_dropped != reported) {
    reported = usb_midi_in_dropped;
    printf("usb midi dropped\t%lu\n", (unsigned long)reported);
  }
#endif
}

#ifdef __cplusplus
}
#endif
#endif
