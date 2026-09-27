class Sequencer {
  bool isPlaying;
  bool isRecording;
  uint8_t len;
  // 128 bytes
  uint8_t mem[128] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};

 public:
  void Init() {
    isPlaying = false;
    isRecording = false;
    len = 0;
  }

  void Reset() { len = 0; }

  void Load(uint8_t save_data_[FLASH_PAGE_SIZE]) {
    for (uint8_t i = 0; i < 128; i++) {
      mem[i] = save_data_[i + 100];
    }
    len = save_data_[98];
    if (save_data_[99] == 1) {
      isPlaying = true;
    }
  }

  void Save(uint8_t save_data_[FLASH_PAGE_SIZE]) {
    if (isPlaying && len > 0) {
      save_data_[99] = 1;
    } else {
      save_data_[99] = 0;
    }
    save_data_[98] = len;
    for (uint8_t i = 0; i < 128; i++) {
      save_data_[i + 100] = mem[i];
    }
  }

  // mem tiene 128 bytes y len es uint8_t: sin este tope, grabar mas de 128
  // beats seguidos escribia fuera del array (a 120 BPM son ~64 s manteniendo un
  // boton, perfectamente alcanzable) y luego len daba la vuelta. Al llegar al
  // tope se deja de grabar y se conserva lo ya capturado.
  void Record(uint8_t v) {
    if (isRecording && len < kMaxSteps) {
      mem[len] = v;
      len++;
    }
  }

  uint8_t Len() { return len; }
  static constexpr uint8_t kMaxSteps = 128;
  bool IsFull() { return len >= kMaxSteps; }

  bool IsPlaying() { return isPlaying && len > 0; }
  bool IsRecording() { return isRecording; }

  void SetRecording(bool on) {
    isRecording = on;
    if (on == true) {
      isPlaying = false;
    }
  }

  void SetPlaying(bool on) {
    isRecording = false;
    isPlaying = on;
  }

  uint8_t Last() {
    if (len > 0) {
      return mem[len - 1];
    }
    return 255;
  }

  uint8_t Next(uint32_t beat) {
    if (isPlaying && len > 0) {
      return mem[beat % len];
    } else {
      return 0;
    }
  }
  // len == 0 daria division por cero; devolvemos 0 (no hay paso actual).
  uint8_t NextI(uint32_t beat) { return len ? (uint8_t)(beat % len) : 0; }
};
