// Drop-in replacement for Knob when there is no ADC hardware.
// Value is driven by buttons via Adjust()/SetBucket() instead of adc_read().
class VirtualKnob {
  uint16_t val;
  bool pending;
  bool changed;

 public:
  void Init(uint8_t input_, uint16_t alpha_) {
    (void)input_;
    (void)alpha_;
    val = 2048;  // mid-scale; nothing is applied until the user adjusts
    pending = false;
    changed = false;
  }

  void Reset() {}

  uint16_t Value() { return val; }
  uint16_t ValueMax() { return 4095; }

  void Adjust(int32_t delta) {
    int32_t v = (int32_t)val + delta;
    if (v < 0) v = 0;
    if (v > 4095) v = 4095;
    if ((uint16_t)v != val) {
      val = (uint16_t)v;
      pending = true;
    }
  }

  // Set to the center of bucket k of `total`, so that
  // Value() * total / ValueMax() == k (used for the selector knob).
  void SetBucket(uint8_t k, uint8_t total) {
    uint32_t v = ((uint32_t)k * 4096u + 2048u) / total;
    if (v > 4095u) v = 4095u;
    if ((uint16_t)v != val) {
      val = (uint16_t)v;
      pending = true;
    }
  }

  // Same contract as Knob: Read() latches, Changed() reports one scan cycle.
  void Read() {
    changed = pending;
    pending = false;
  }

  bool Changed() { return changed; }
};
