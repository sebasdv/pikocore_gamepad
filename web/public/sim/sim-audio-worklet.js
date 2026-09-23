// web/public/sim/sim-audio-worklet.js
class SimAudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.queue = [];
    this.port.onmessage = (event) => {
      // event.data is a Float32Array of PCM samples at sampleRate (48000, matches
      // sim::kAudioRate; the AudioContext must be created with { sampleRate: 48000 }).
      this.queue.push(event.data);
    };
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
      if (take === chunk.length) {
        this.queue.shift();
      } else {
        this.queue[0] = chunk.subarray(take);
      }
    }
    return true;
  }
}

registerProcessor('sim-audio-processor', SimAudioProcessor);
