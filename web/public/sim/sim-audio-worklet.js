// web/public/sim/sim-audio-worklet.js
class SimAudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.queue = [];
    // Running total of frames across every chunk in `queue`, maintained incrementally
    // on push/shift/partial-consume rather than recomputed by summing `queue` each time
    // (this runs on the audio thread — keep it O(1) per process() call).
    this.queuedFrames = 0;
    // Backstop cap (Critical 1, defensive layer 2): the main thread throttles how much
    // audio it produces based on our reported queue depth (see SimDemo.tsx), but if that
    // throttle is ever bypassed or lags, never let the queue grow past ~100ms of audio —
    // drop the oldest chunks instead of growing unboundedly.
    this.maxQueuedFrames = Math.round(sampleRate * 0.1);
    // Report queue depth back to the main thread periodically rather than every
    // process() call (a process() call covers only 128 frames / ~2.7ms at 48kHz;
    // reporting every 8th call is ~21ms cadence, plenty fine-grained for pacing).
    this.processCountSinceReport = 0;
    this.reportEveryNProcess = 8;

    this.port.onmessage = (event) => {
      // Incoming messages from the main thread are always Float32Array PCM chunks at
      // sampleRate (48000, matches sim::kAudioRate; the AudioContext must be created
      // with { sampleRate: 48000 }). Guard against any other shape rather than assume.
      if (!(event.data instanceof Float32Array)) return;
      this.queue.push(event.data);
      this.queuedFrames += event.data.length;
      this._enforceCap();
    };
  }

  _enforceCap() {
    while (this.queuedFrames > this.maxQueuedFrames && this.queue.length > 0) {
      const dropped = this.queue.shift();
      this.queuedFrames -= dropped.length;
    }
  }

  process(_inputs, outputs) {
    const output = outputs[0][0];
    let i = 0;
    while (i < output.length) {
      if (this.queue.length === 0) {
        output.fill(0, i);  // underrun: silence, same fallback the native WASAPI path has
        break;
      }
      const chunk = this.queue[0];
      const take = Math.min(chunk.length, output.length - i);
      output.set(chunk.subarray(0, take), i);
      i += take;
      this.queuedFrames -= take;
      if (take === chunk.length) {
        this.queue.shift();
      } else {
        this.queue[0] = chunk.subarray(take);
      }
    }

    this.processCountSinceReport++;
    if (this.processCountSinceReport >= this.reportEveryNProcess) {
      this.processCountSinceReport = 0;
      this.port.postMessage({ queuedFrames: this.queuedFrames });
    }
    return true;
  }
}

registerProcessor('sim-audio-processor', SimAudioProcessor);
