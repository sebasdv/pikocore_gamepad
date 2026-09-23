import { useCallback, useEffect, useRef, useState } from 'react';
import { keyToButtonBit } from './keyboard';
import { pollGamepadMask } from './gamepad';
import { PikoSim } from './simModule';

const LCD_SIZE = 240;
const AUDIO_SAMPLE_RATE = 48000;
// See SimDemo.tsx's original comment (now here): 30ms mirrors sim::should_step's
// ~20ms kLeadFrames target (sim/web/main.cpp) plus ~10ms margin for rAF jitter.
const AUDIO_LEAD_THRESHOLD_FRAMES = Math.round(AUDIO_SAMPLE_RATE * 0.03);

export type SimStatus = 'idle' | 'loading' | 'ready';

export interface UsePikoSimResult {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  status: SimStatus;
  error: string | null;
  start: () => void;
}

export function usePikoSim(extraMaskRef: { current: number }): UsePikoSimResult {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const simRef = useRef<PikoSim | null>(null);
  const keyMaskRef = useRef(0);
  const gamepadIndexRef = useRef<number | null>(null);
  const rafRef = useRef(0);
  const audioQueuedFramesRef = useRef(0);
  const startedRef = useRef(false);
  const teardownRef = useRef<(() => void) | null>(null);
  const [status, setStatus] = useState<SimStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  const start = useCallback(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    setStatus('loading');

    let cancelled = false;
    let audioContext: AudioContext | null = null;
    let workletNode: AudioWorkletNode | null = null;

    async function boot() {
      try {
        const sim = await PikoSim.create();
        if (cancelled) return;
        simRef.current = sim;

        audioContext = new AudioContext({ sampleRate: AUDIO_SAMPLE_RATE });
        await audioContext.audioWorklet.addModule(`${import.meta.env.BASE_URL}sim/sim-audio-worklet.js`);
        if (cancelled) return;
        workletNode = new AudioWorkletNode(audioContext, 'sim-audio-processor');
        workletNode.connect(audioContext.destination);
        workletNode.port.onmessage = (event) => {
          const data = event.data as unknown;
          if (data && typeof data === 'object' && 'queuedFrames' in data) {
            audioQueuedFramesRef.current = (data as { queuedFrames: number }).queuedFrames;
          }
        };

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

        setStatus('ready');
        canvas?.focus();

        let lastFrameTime = performance.now();
        const tick = () => {
          const now = performance.now();
          const budgetMs = Math.min(50, now - lastFrameTime);
          lastFrameTime = now;

          let mask = keyMaskRef.current | extraMaskRef.current;
          const gamepadIndex = gamepadIndexRef.current;
          if (gamepadIndex != null) {
            const pad = navigator.getGamepads()[gamepadIndex];
            if (pad) mask |= pollGamepadMask(pad, sim);
          }
          sim.setButtons(mask);

          const audioQueuedFrames = audioQueuedFramesRef.current;
          const shouldAdvance = audioQueuedFrames < AUDIO_LEAD_THRESHOLD_FRAMES;
          if (shouldAdvance) sim.step(budgetMs);

          const frame = sim.getLcdFrame();
          const canvasEl = canvasRef.current;
          const ctx = canvasEl?.getContext('2d');
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
        return undefined;
      }
    }

    const cleanupPromise = boot();
    teardownRef.current = () => {
      cancelled = true;
      cancelAnimationFrame(rafRef.current);
      void cleanupPromise.then((cleanup) => cleanup?.());
      workletNode?.disconnect();
      void audioContext?.close();
    };
    // extraMaskRef is a stable ref object identity for the lifetime of the caller
    // (created once via useRef in PlayTab) — safe to omit from deps in practice,
    // but included since it's referenced inside this callback.
  }, [extraMaskRef]);

  useEffect(() => {
    return () => {
      teardownRef.current?.();
    };
  }, []);

  return { canvasRef, status, error, start };
}
