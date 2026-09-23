#include "platform/audio_out.h"

#include <windows.h>
#include <mmreg.h>
#include <audioclient.h>
#include <ksmedia.h>
#include <mmdeviceapi.h>

#include <cstdio>
#include <vector>

namespace sim {

namespace {
template <class T>
void release(T*& p) {
  if (p != nullptr) {
    p->Release();
    p = nullptr;
  }
}
}  // namespace

AudioOut::~AudioOut() { stop(); }

bool AudioOut::start(AudioRing* ring, std::string* err) {
  ready_ = std::promise<std::string>();
  std::future<std::string> result = ready_.get_future();
  quit_ = false;
  failed_ = false;
  thread_ = std::thread([this, ring] { run(ring); });
  const std::string failure = result.get();
  if (!failure.empty()) {
    thread_.join();
    if (err != nullptr) *err = failure;
    return false;
  }
  return true;
}

void AudioOut::stop() {
  quit_ = true;
  if (thread_.joinable()) thread_.join();
}

void AudioOut::run(AudioRing* ring) {
  CoInitializeEx(nullptr, COINIT_MULTITHREADED);
  IMMDeviceEnumerator* enumerator = nullptr;
  IMMDevice* device = nullptr;
  IAudioClient* client = nullptr;
  IAudioRenderClient* render = nullptr;
  HANDLE event = CreateEventW(nullptr, FALSE, FALSE, nullptr);

  WAVEFORMATEXTENSIBLE fmt = {};
  fmt.Format.wFormatTag = WAVE_FORMAT_EXTENSIBLE;
  fmt.Format.nChannels = 2;
  fmt.Format.nSamplesPerSec = 48000;
  fmt.Format.wBitsPerSample = 32;
  fmt.Format.nBlockAlign = 8;
  fmt.Format.nAvgBytesPerSec = 48000 * 8;
  fmt.Format.cbSize = sizeof(WAVEFORMATEXTENSIBLE) - sizeof(WAVEFORMATEX);
  fmt.Samples.wValidBitsPerSample = 32;
  fmt.dwChannelMask = SPEAKER_FRONT_LEFT | SPEAKER_FRONT_RIGHT;
  fmt.SubFormat = KSDATAFORMAT_SUBTYPE_IEEE_FLOAT;

  UINT32 buffer_frames = 0;
  HRESULT hr = CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
                                __uuidof(IMMDeviceEnumerator), reinterpret_cast<void**>(&enumerator));
  if (SUCCEEDED(hr)) hr = enumerator->GetDefaultAudioEndpoint(eRender, eConsole, &device);
  if (SUCCEEDED(hr)) {
    hr = device->Activate(__uuidof(IAudioClient), CLSCTX_ALL, nullptr,
                          reinterpret_cast<void**>(&client));
  }
  if (SUCCEEDED(hr)) {
    hr = client->Initialize(AUDCLNT_SHAREMODE_SHARED,
                            AUDCLNT_STREAMFLAGS_EVENTCALLBACK | AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM |
                                AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY,
                            100000 /* 10 ms */, 0, &fmt.Format, nullptr);
  }
  if (SUCCEEDED(hr)) hr = client->SetEventHandle(event);
  if (SUCCEEDED(hr)) hr = client->GetBufferSize(&buffer_frames);
  if (SUCCEEDED(hr)) {
    hr = client->GetService(__uuidof(IAudioRenderClient), reinterpret_cast<void**>(&render));
  }
  if (SUCCEEDED(hr)) hr = client->Start();

  std::string failure;
  if (FAILED(hr)) {
    char msg[64];
    std::snprintf(msg, sizeof(msg), "WASAPI falló (0x%08lx)", static_cast<unsigned long>(hr));
    failure = msg;
  }
  ready_.set_value(failure);  // después de esto no se toca más `ready_`

  std::vector<float> mono(buffer_frames);
  while (failure.empty() && !quit_) {
    WaitForSingleObject(event, 100);
    UINT32 padding = 0;
    if (FAILED(client->GetCurrentPadding(&padding))) {
      failed_ = true;
      break;
    }
    const UINT32 avail = buffer_frames - padding;
    if (avail == 0) continue;
    BYTE* data = nullptr;
    if (FAILED(render->GetBuffer(avail, &data))) {
      failed_ = true;
      break;
    }
    const size_t got = ring->pop(mono.data(), avail);
    float* out = reinterpret_cast<float*>(data);
    for (UINT32 i = 0; i < avail; ++i) {
      const float s = i < got ? mono[i] : 0.0f;
      out[2 * i] = s;
      out[2 * i + 1] = s;
    }
    render->ReleaseBuffer(avail, 0);
    consumed_ += avail;
  }

  if (client != nullptr) client->Stop();
  release(render);
  release(client);
  release(device);
  release(enumerator);
  CloseHandle(event);
  CoUninitialize();
}

}  // namespace sim
