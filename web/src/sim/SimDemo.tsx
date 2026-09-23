import { useEffect, useRef, useState } from 'react';
import { keyToButtonBit } from './keyboard';
import { pollGamepadMask } from './gamepad';
import { PikoSim } from './simModule';

const LCD_SIZE = 240;
const AUDIO_SAMPLE_RATE = 48000;
// Critical 1 fix: throttle emulation/audio production by the AudioWorkletProcessor's
// *actual* reported queue depth instead of the C++ AudioRing's fill level. In the web
// port, pullAudio() drains the ring into the worklet in one big chunk every rAF, so the
// ring itself is a useless backpressure signal (it reads near-empty right after each
// drain regardless of how much audio is still queued, unplayed, inside the worklet).
// 30ms mirrors sim::should_step's ~20ms kLeadFrames target (see sim/web/main.cpp) plus
// ~10ms of margin to absorb rAF scheduling jitter, since this throttle reacts to a
// worklet message that lags real playback by up to one reporting interval.
const AUDIO_LEAD_THRESHOLD_FRAMES = Math.round(AUDIO_SAMPLE_RATE * 0.03);

export function SimDemo() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const simRef = useRef<PikoSim | null>(null);
  const keyMaskRef = useRef(0);
  const gamepadIndexRef = useRef<number | null>(null);
  const rafRef = useRef(0);
  const audioQueuedFramesRef = useRef(0);
  const [status, setStatus] = useState('Loading simulator...');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let audioContext: AudioContext | null = null;
    let workletNode: AudioWorkletNode | null = null;

    async function boot() {
      try {
        const sim = await PikoSim.create();
        if (cancelled) return;
        simRef.current = sim;

        audioContext = new AudioContext({ sampleRate: 48000 });
        await audioContext.audioWorklet.addModule(`${import.meta.env.BASE_URL}sim/sim-audio-worklet.js`);
        if (cancelled) return;
        workletNode = new AudioWorkletNode(audioContext, 'sim-audio-processor');
        workletNode.connect(audioContext.destination);
        workletNode.port.onmessage = (event) => {
          // The worklet only ever posts { queuedFrames } status objects back to us (the
          // PCM data flows the other way, main thread -> worklet); guard the shape anyway.
          const data = event.data as unknown;
          if (data && typeof data === 'object' && 'queuedFrames' in data) {
            audioQueuedFramesRef.current = (data as { queuedFrames: number }).queuedFrames;
          }
        };

        // Important 5 fix: Safari can leave the AudioContext suspended (autoplay policy)
        // because it's constructed after several awaits, outside the synchronous scope of
        // the click that triggered boot(). resume() on an already-running context is a
        // harmless no-op per spec, so call it from the very next user gesture too.
        const resumeAudio = () => {
          void audioContext?.resume();
        };

        const onKeyDown = (event: KeyboardEvent) => {
          resumeAudio();
          const bit = keyToButtonBit(event.code);
          if (bit != null) {
            keyMaskRef.current |= bit;
            event.preventDefault();
          }
        };
        const onKeyUp = (event: KeyboardEvent) => {
          const bit = keyToButtonBit(event.code);
          if (bit != null) {
            keyMaskRef.current &= ~bit;
            event.preventDefault();
          }
        };
        const canvas = canvasRef.current;
        canvas?.setAttribute('tabindex', '0');
        canvas?.addEventListener('keydown', onKeyDown);
        canvas?.addEventListener('keyup', onKeyUp);
        canvas?.addEventListener('pointerdown', resumeAudio);

        const onGamepadConnected = (event: GamepadEvent) => {
          gamepadIndexRef.current = event.gamepad.index;
        };
        const onGamepadDisconnected = (event: GamepadEvent) => {
          if (gamepadIndexRef.current === event.gamepad.index) gamepadIndexRef.current = null;
        };
        window.addEventListener('gamepadconnected', onGamepadConnected);
        window.addEventListener('gamepaddisconnected', onGamepadDisconnected);

        setStatus('Ready');
        // Important 4 fix: keyboard listeners are canvas-scoped, so without focusing the
        // canvas here, keys pressed right after "Ready" do nothing until the user clicks it.
        canvas?.focus();

        let lastFrameTime = performance.now();
        const tick = () => {
          const now = performance.now();
          const budgetMs = Math.min(50, now - lastFrameTime);
          lastFrameTime = now;

          let mask = keyMaskRef.current;
          const gamepadIndex = gamepadIndexRef.current;
          if (gamepadIndex != null) {
            const pad = navigator.getGamepads()[gamepadIndex];
            if (pad) mask |= pollGamepadMask(pad, sim);
          }
          sim.setButtons(mask);

          // Critical 1 fix: only advance emulation (and therefore produce more audio)
          // while the worklet's actual queue has room. Otherwise skip stepping this
          // frame entirely — piling more audio onto an already-full queue is exactly
          // what caused latency to grow without bound.
          const audioQueuedFrames = audioQueuedFramesRef.current;
          const shouldAdvance = audioQueuedFrames < AUDIO_LEAD_THRESHOLD_FRAMES;
          if (shouldAdvance) {
            sim.step(budgetMs);
          }

          const frame = sim.getLcdFrame();
          const canvas = canvasRef.current;
          const ctx = canvas?.getContext('2d');
          if (ctx) {
            const imageData = ctx.getImageData(0, 0, LCD_SIZE, LCD_SIZE);
            for (let i = 0; i < frame.length; i++) {
              const px = frame[i];
              const r = ((px >> 11) & 0x1f) * 255 / 31;
              const g = ((px >> 5) & 0x3f) * 255 / 63;
              const b = (px & 0x1f) * 255 / 31;
              imageData.data[i * 4] = r;
              imageData.data[i * 4 + 1] = g;
              imageData.data[i * 4 + 2] = b;
              imageData.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(imageData, 0, 0);
          }

          if (shouldAdvance) {
            const audio = sim.pullAudio(4096);
            if (audio.length > 0 && workletNode) workletNode.port.postMessage(audio);
          }

          rafRef.current = requestAnimationFrame(tick);
        };
        rafRef.current = requestAnimationFrame(tick);

        return () => {
          canvas?.removeEventListener('keydown', onKeyDown);
          canvas?.removeEventListener('keyup', onKeyUp);
          canvas?.removeEventListener('pointerdown', resumeAudio);
          window.removeEventListener('gamepadconnected', onGamepadConnected);
          window.removeEventListener('gamepaddisconnected', onGamepadDisconnected);
        };
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    }

    const cleanupPromise = boot();

    return () => {
      cancelled = true;
      cancelAnimationFrame(rafRef.current);
      void cleanupPromise.then((cleanup) => cleanup?.());
      workletNode?.disconnect();
      void audioContext?.close();
    };
  }, []);

  return (
    <div className="sim-demo">
      {error ? (
        <div className="sim-demo-error">Simulator failed to load: {error}</div>
      ) : (
        <>
          <canvas ref={canvasRef} width={LCD_SIZE} height={LCD_SIZE} className="sim-demo-canvas" />
          <div className="sim-demo-status">{status}</div>
          <div className="sim-demo-legend">
            <span>Click the screen to enable keyboard controls</span>
            <span>Arrows / WASD: D-pad + face buttons</span>
            <span>Q / E: L / R</span>
            <span>Backspace / Enter: Select / Start</span>
            <span>Xbox-compatible gamepad also works</span>
          </div>
        </>
      )}
    </div>
  );
}
