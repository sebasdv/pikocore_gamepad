import { useEffect, useRef, useState } from 'react';
import { keyToButtonBit } from './keyboard';
import { pollGamepadMask } from './gamepad';
import { PikoSim } from './simModule';

const LCD_SIZE = 240;

export function SimDemo() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const simRef = useRef<PikoSim | null>(null);
  const keyMaskRef = useRef(0);
  const gamepadIndexRef = useRef<number | null>(null);
  const rafRef = useRef(0);
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

        const onKeyDown = (event: KeyboardEvent) => {
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

        const onGamepadConnected = (event: GamepadEvent) => {
          gamepadIndexRef.current = event.gamepad.index;
        };
        const onGamepadDisconnected = (event: GamepadEvent) => {
          if (gamepadIndexRef.current === event.gamepad.index) gamepadIndexRef.current = null;
        };
        window.addEventListener('gamepadconnected', onGamepadConnected);
        window.addEventListener('gamepaddisconnected', onGamepadDisconnected);

        setStatus('Ready');

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
          sim.step(budgetMs);

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

          const audio = sim.pullAudio(4096);
          if (audio.length > 0 && workletNode) workletNode.port.postMessage(audio);

          rafRef.current = requestAnimationFrame(tick);
        };
        rafRef.current = requestAnimationFrame(tick);

        return () => {
          canvas?.removeEventListener('keydown', onKeyDown);
          canvas?.removeEventListener('keyup', onKeyUp);
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
