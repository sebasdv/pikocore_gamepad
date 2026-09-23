# Virtual Gamepad "Play" Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing collapsible "Try it in your browser" demo into a dedicated, mobile-first "Play" tab in the web loader: a landscape-only virtual pikocore gamepad with on-screen touch controls laid out like the real GamePi13, alongside the keyboard and physical Gamepad API support that already work.

**Architecture:** Extract the existing `SimDemo.tsx`'s boot/render-loop logic into a reusable `usePikoSim` hook, gated behind an explicit `start()` call instead of auto-booting on mount. Build a new `GamepadControls` component (D-pad, face-button diamond, shoulder buttons, Select/Start) using Pointer Events so multiple buttons can be held at once. Compose both into a new `PlayTab` component with an orientation gate (portrait → "rotate your phone") and a boot gate (idle → "Play" button → loading → ready). Wire a two-tab switcher into `App.tsx` and delete `SimDemo.tsx`.

**Tech Stack:** React 19 (existing), TypeScript, Pointer Events (no new dependencies).

## Global Constraints

- Reused unchanged: `PikoSim` (`web/src/sim/simModule.ts`), `keyToButtonBit`/`BUTTON_BITS` (`web/src/sim/keyboard.ts`), `pollGamepadMask` (`web/src/sim/gamepad.ts`), `sim-audio-worklet.js`. None of these files are modified by this plan.
- The Play tab is landscape-only. Portrait shows a "rotate your phone" message; there is no separate portrait control layout.
- The simulator does not auto-boot when the Play tab is opened — it waits for an explicit "Play" button tap, both to avoid spending mobile data unprompted and to guarantee a clean user gesture for `AudioContext` (Safari's autoplay policy).
- Face-button position mapping must match `keyboard.ts`'s existing convention exactly: top = X, right = A, bottom = B, left = Y (`BUTTON_BITS.X/A/B/Y`).
- Touch buttons use Pointer Events (`onPointerDown`/`onPointerUp`/`onPointerCancel`), not `onClick` — multiple buttons must be holdable at once (the firmware's combos require it: Select+music button, Start+L/R, two face buttons together).
- No new npm dependencies.
- Spec: [docs/superpowers/specs/2026-09-23-web-sim-gamepad-design.md](../specs/2026-09-23-web-sim-gamepad-design.md)

---

## File Structure

```
web/src/sim/usePikoSim.ts       new — boot/rAF-loop/cleanup hook, gated behind start()
web/src/sim/GamepadControls.tsx new — touch D-pad/faces/shoulders/Select+Start layout
web/src/sim/PlayTab.tsx         new — orientation gate, Play-button gate, composes the above
web/src/sim/SimDemo.tsx         deleted — logic now split across the three files above
web/src/App.tsx                 modified — tab state/switcher, removes Monitor button and
                                  sim-demo-section, renders <PlayTab /> for the Play tab
web/src/styles.css              modified — tab switcher, Play tab layout/orientation gate,
                                  gamepad button grid styles
```

---

### Task 1: `usePikoSim` hook — extract the boot/loop logic, gated behind `start()`

**Files:**
- Create: `web/src/sim/usePikoSim.ts`

**Interfaces:**
- Consumes: `PikoSim` (`web/src/sim/simModule.ts`), `keyToButtonBit` (`web/src/sim/keyboard.ts`), `pollGamepadMask` (`web/src/sim/gamepad.ts`) — all unchanged.
- Produces: `usePikoSim(extraMaskRef: { current: number }): { canvasRef: React.RefObject<HTMLCanvasElement | null>; status: 'idle' | 'loading' | 'ready'; error: string | null; start: () => void }`. `extraMaskRef` is a caller-owned mutable ref (e.g. touch controls' pressed-button mask) that gets OR'd into the button mask every frame, alongside this hook's own keyboard/gamepad handling. Task 3 (`PlayTab`) creates this ref and passes the same object to both this hook and `GamepadControls`.

This is a refactor of `web/src/sim/SimDemo.tsx`'s existing `useEffect` (read it first — it's the exact logic being moved) with one behavioral change: instead of booting automatically inside a mount effect, the boot sequence only runs when the caller calls `start()`. The teardown-on-unmount behavior must stay exactly as robust as the original — that closure shape was already independently verified correct (traced in detail by a prior code review; no leak, handles cancellation mid-boot) — preserve it, don't redesign it.

```typescript
// web/src/sim/usePikoSim.ts
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
```

- [ ] **Step 1: Write `usePikoSim.ts` exactly as above.**

- [ ] **Step 2: Typecheck**

```bash
cd web && npx tsc --noEmit
```

Expected: no errors. If TypeScript complains about `extraMaskRef`'s type not matching a `RefObject`/`MutableRefObject` expectation anywhere, the `{ current: number }` plain-object type used here is deliberate — keep it as a plain object type rather than importing React's ref types, to sidestep any version-specific ref-mutability typing differences.

- [ ] **Step 3: Commit**

```bash
git add web/src/sim/usePikoSim.ts
git commit -m "web: extract usePikoSim hook, boot gated behind start()"
```

---

### Task 2: `GamepadControls` — touch button layout

**Files:**
- Create: `web/src/sim/GamepadControls.tsx`

**Interfaces:**
- Consumes: `BUTTON_BITS` (`web/src/sim/keyboard.ts`, unchanged).
- Produces: `GamepadControls({ maskRef, children }: { maskRef: { current: number }; children: React.ReactNode }): JSX.Element`. `children` is rendered inside the screen slot (Task 3 passes the LCD `<canvas>`). Writes into `maskRef.current` on press/release — the same ref object Task 1's `usePikoSim` reads from every frame via its `extraMaskRef` parameter.

```tsx
// web/src/sim/GamepadControls.tsx
import { useRef } from 'react';
import { BUTTON_BITS } from './keyboard';

interface TouchButtonProps {
  bit: number;
  maskRef: { current: number };
  label: string;
  className: string;
}

// Tracks its own held pointer IDs (a Set, not a boolean) so two fingers briefly
// overlapping the same button — or a stray duplicate pointerdown — can't cause
// one finger's lift to clear a bit the other finger is still holding.
function TouchButton({ bit, maskRef, label, className }: TouchButtonProps) {
  const pointersRef = useRef<Set<number>>(new Set());

  const press = (pointerId: number) => {
    pointersRef.current.add(pointerId);
    maskRef.current |= bit;
  };
  const release = (pointerId: number) => {
    pointersRef.current.delete(pointerId);
    if (pointersRef.current.size === 0) maskRef.current &= ~bit;
  };

  return (
    <button
      type="button"
      className={`gamepad-btn ${className}`}
      onPointerDown={(event) => {
        event.preventDefault();
        (event.target as Element).setPointerCapture(event.pointerId);
        press(event.pointerId);
      }}
      onPointerUp={(event) => release(event.pointerId)}
      onPointerCancel={(event) => release(event.pointerId)}
      aria-label={label}
    >
      {label}
    </button>
  );
}

export function GamepadControls({
  maskRef,
  children,
}: {
  maskRef: { current: number };
  children: React.ReactNode;
}) {
  return (
    <div className="play-gamepad">
      <div className="play-gamepad-l">
        <TouchButton bit={BUTTON_BITS.L} maskRef={maskRef} label="L" className="gamepad-shoulder-btn" />
      </div>
      <div className="play-gamepad-r">
        <TouchButton bit={BUTTON_BITS.R} maskRef={maskRef} label="R" className="gamepad-shoulder-btn" />
      </div>
      <div className="play-gamepad-dpad">
        <TouchButton bit={BUTTON_BITS.UP} maskRef={maskRef} label="↑" className="gamepad-dpad-up" />
        <TouchButton bit={BUTTON_BITS.LEFT} maskRef={maskRef} label="←" className="gamepad-dpad-left" />
        <TouchButton bit={BUTTON_BITS.RIGHT} maskRef={maskRef} label="→" className="gamepad-dpad-right" />
        <TouchButton bit={BUTTON_BITS.DOWN} maskRef={maskRef} label="↓" className="gamepad-dpad-down" />
      </div>
      <div className="play-gamepad-screen">{children}</div>
      <div className="play-gamepad-center">
        <TouchButton bit={BUTTON_BITS.SELECT} maskRef={maskRef} label="Select" className="gamepad-center-btn" />
        <TouchButton bit={BUTTON_BITS.START} maskRef={maskRef} label="Start" className="gamepad-center-btn" />
      </div>
      <div className="play-gamepad-faces">
        {/* Position-based mapping, matching keyboard.ts exactly: top=X, right=A, bottom=B, left=Y */}
        <TouchButton bit={BUTTON_BITS.X} maskRef={maskRef} label="X" className="gamepad-face-top" />
        <TouchButton bit={BUTTON_BITS.Y} maskRef={maskRef} label="Y" className="gamepad-face-left" />
        <TouchButton bit={BUTTON_BITS.A} maskRef={maskRef} label="A" className="gamepad-face-right" />
        <TouchButton bit={BUTTON_BITS.B} maskRef={maskRef} label="B" className="gamepad-face-bottom" />
      </div>
    </div>
  );
}
```

- [ ] **Step 1: Write `GamepadControls.tsx` exactly as above.**

- [ ] **Step 2: Add the grid layout CSS to `web/src/styles.css`.** Read the file's existing custom properties first (`--border-strong`, `--control`, `--text` are already defined and used by `.sim-demo-canvas`/`.icon-button` — reuse them, don't introduce new color values):

```css
.play-gamepad {
  display: grid;
  grid-template-columns: auto 1fr auto;
  grid-template-rows: auto 1fr auto;
  grid-template-areas:
    "l      .      r"
    "dpad   screen faces"
    "dpad   center faces";
  gap: 12px;
  width: 100%;
  height: 100%;
  padding: 12px;
  align-items: center;
  justify-items: center;
}

.play-gamepad-l { grid-area: l; justify-self: start; }
.play-gamepad-r { grid-area: r; justify-self: end; }
.play-gamepad-dpad { grid-area: dpad; }
.play-gamepad-faces { grid-area: faces; }
.play-gamepad-center { grid-area: center; display: flex; gap: 8px; }
.play-gamepad-screen {
  grid-area: screen;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  max-height: 100%;
}

.play-gamepad-dpad,
.play-gamepad-faces {
  display: grid;
  grid-template-columns: repeat(3, 44px);
  grid-template-rows: repeat(3, 44px);
}
.play-gamepad-dpad {
  grid-template-areas:
    ".    up   ."
    "left .    right"
    ".    down .";
}
.play-gamepad-faces {
  grid-template-areas:
    ".     top    ."
    "left  .      right"
    ".     bottom .";
}
.gamepad-dpad-up { grid-area: up; }
.gamepad-dpad-left { grid-area: left; }
.gamepad-dpad-right { grid-area: right; }
.gamepad-dpad-down { grid-area: down; }
.gamepad-face-top { grid-area: top; }
.gamepad-face-left { grid-area: left; }
.gamepad-face-right { grid-area: right; }
.gamepad-face-bottom { grid-area: bottom; }

.gamepad-btn {
  width: 44px;
  height: 44px;
  border: 2px solid var(--border-strong);
  background: var(--control);
  color: var(--text);
  border-radius: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  padding: 0;
  user-select: none;
  touch-action: none;
  -webkit-tap-highlight-color: transparent;
}
.gamepad-btn:active {
  background: var(--text);
  color: #000000;
}
.gamepad-shoulder-btn { width: 64px; height: 40px; }
.gamepad-center-btn { width: 60px; height: 32px; font-size: 12px; }
```

`touch-action: none` stops the browser's own scroll/zoom gestures from stealing pointer events meant for these buttons — required for reliable multi-touch on mobile.

- [ ] **Step 3: Typecheck**

```bash
cd web && npx tsc --noEmit
```

Expected: no errors. `GamepadControls.tsx` isn't wired into the app yet (Task 3 does that) — this step only confirms the file itself compiles standalone.

- [ ] **Step 4: Commit**

```bash
git add web/src/sim/GamepadControls.tsx web/src/styles.css
git commit -m "web: touch gamepad controls (D-pad, faces, shoulders, Select/Start)"
```

---

### Task 3: `PlayTab` — orientation gate, boot gate, composition

**Files:**
- Create: `web/src/sim/PlayTab.tsx`

**Interfaces:**
- Consumes: `usePikoSim` (Task 1), `GamepadControls` (Task 2).
- Produces: `export function PlayTab(): JSX.Element`, mounted from `App.tsx` (Task 4).

```tsx
// web/src/sim/PlayTab.tsx
import { useRef } from 'react';
import { usePikoSim } from './usePikoSim';
import { GamepadControls } from './GamepadControls';

const LCD_SIZE = 240;

export function PlayTab() {
  const touchMaskRef = useRef(0);
  const { canvasRef, status, error, start } = usePikoSim(touchMaskRef);

  return (
    <div className="play-tab">
      <div className="play-rotate-hint">
        <span>Rotate your phone to play</span>
      </div>
      <div className="play-content">
        {error ? (
          <div className="sim-demo-error play-error">Simulator failed to load: {error}</div>
        ) : status === 'idle' ? (
          <div className="play-start-screen">
            <h2>pikocore — play in your browser</h2>
            <p>Try the device right here, no install needed.</p>
            <button type="button" className="primary play-button" onClick={start}>
              Play
            </button>
          </div>
        ) : status === 'loading' ? (
          <div className="play-start-screen">
            <span className="spinner" aria-hidden="true" />
            <p>Loading simulator...</p>
          </div>
        ) : (
          <GamepadControls maskRef={touchMaskRef}>
            <canvas ref={canvasRef} width={LCD_SIZE} height={LCD_SIZE} className="sim-demo-canvas" />
          </GamepadControls>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 1: Write `PlayTab.tsx` exactly as above.**

- [ ] **Step 2: Add the tab-level and orientation-gate CSS to `web/src/styles.css`.**

```css
.play-tab {
  position: relative;
  width: 100%;
  min-height: 70vh;
}

.play-rotate-hint {
  display: none;
}

.play-content {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  min-height: 70vh;
}

.play-start-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
  padding: 24px;
}

.play-button {
  height: 48px;
  padding: 0 28px;
  font-size: 16px;
}

.play-error {
  max-width: 480px;
  margin: 24px;
}

@media (orientation: portrait) {
  .play-rotate-hint {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 70vh;
    text-align: center;
    padding: 24px;
    color: var(--muted);
  }
  .play-content {
    display: none;
  }
}
```

`.sim-demo-canvas` and `.sim-demo-error` already exist from the prior demo (`.app .sim-demo-canvas { image-rendering: pixelated; width: 240px; height: 240px; ...}`, `.app .sim-demo-error { border: 2px solid var(--text); background: var(--text); color: #000000; padding: 8px 10px; }`) — reused here as-is, do not duplicate their rules under a new class name.

- [ ] **Step 3: Typecheck**

```bash
cd web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add web/src/sim/PlayTab.tsx web/src/styles.css
git commit -m "web: PlayTab — orientation gate, Play-button boot gate, gamepad layout"
```

---

### Task 4: Wire the tab switcher into `App.tsx`, remove the old demo

**Files:**
- Modify: `web/src/App.tsx`
- Modify: `web/src/styles.css`
- Delete: `web/src/sim/SimDemo.tsx`

**Interfaces:**
- Consumes: `PlayTab` (Task 3).
- Produces: nothing new exported — this task changes `App`'s internal structure only.

Read the current `web/src/App.tsx` before editing — line numbers below are approximate (the file has moved slightly since this plan was written); locate each anchor by its actual content.

- [ ] **Step 1: Remove the old demo's wiring.**
  - Delete the import `import { SimDemo } from './sim/SimDemo';`.
  - Delete `import { Monitor } from 'lucide-react'` from the `lucide-react` import list — **check first** whether anything else in the file still uses `Monitor`; if not, remove just that one name from the import list, keeping the others.
  - Delete the `const [simDemoOpen, setSimDemoOpen] = useState(false);` line.
  - Delete the `<button className="icon-button" onClick={() => setSimDemoOpen(...)} ...><Monitor size={18} /></button>` block from the toolbar.
  - Delete the `{simDemoOpen ? (<section className="sim-demo-section">...<SimDemo /></section>) : null}` block.

- [ ] **Step 2: Add tab state.** Near the other `useState` calls:

```tsx
  const [tab, setTab] = useState<'loader' | 'play'>('loader');
```

- [ ] **Step 3: Add the `PlayTab` import** alongside the other local imports:

```tsx
import { PlayTab } from './sim/PlayTab';
```

- [ ] **Step 4: Add the tab switcher and wrap the existing page content.** The current `return (<main className="app"> ... </main>)` renders the header, all the modals/sections, the sample list, and the footer unconditionally. Restructure so:
  1. A tab switcher renders unconditionally, as the first child of `<main className="app">`.
  2. Everything that currently follows (the `<header>` through the `<footer>`, i.e. everything that was already there) is wrapped in a `tab === 'loader' ? (<>...</>) : null` fragment.
  3. `<PlayTab />` renders when `tab === 'play'`.

```tsx
  return (
    <main className="app">
      <nav className="tab-switcher">
        <button
          type="button"
          className={tab === 'loader' ? 'active' : undefined}
          aria-pressed={tab === 'loader'}
          onClick={() => setTab('loader')}
        >
          Loader
        </button>
        <button
          type="button"
          className={tab === 'play' ? 'active' : undefined}
          aria-pressed={tab === 'play'}
          onClick={() => setTab('play')}
        >
          Play
        </button>
      </nav>

      {tab === 'loader' ? (
        <>
          {/* everything that was already here: <header className="topbar">...</header>,
              the incompatibleDevice/ittybittymidiInfoOpen/controlsInfoOpen blocks, the
              capacity section, the debugOpen block, the sample-list section, and the
              footer — unchanged, just wrapped in this fragment */}
        </>
      ) : (
        <PlayTab />
      )}
    </main>
  );
```

Do not change anything inside that fragment's content beyond what Step 1 already removed (the Monitor button and the sim-demo-section block) — this is a wrapping change, not a rewrite of the Loader tab's own markup.

- [ ] **Step 5: Delete `web/src/sim/SimDemo.tsx`.**

```bash
git rm web/src/sim/SimDemo.tsx
```

- [ ] **Step 6: Add tab switcher CSS to `web/src/styles.css`**, matching the existing `.icon-button`/`.status` monochrome conventions (hard borders, no color, `aria-pressed`/active state via border+background inversion — read `.app .icon-button[aria-pressed="true"]`'s existing rule and reuse the same inversion pattern):

```css
.app .tab-switcher {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}

.app .tab-switcher button {
  height: 36px;
  padding: 0 18px;
  border: 2px solid var(--border-strong);
  background: var(--control);
  color: var(--text);
  border-radius: 0;
  cursor: pointer;
}

.app .tab-switcher button.active {
  background: var(--text);
  color: #000000;
}
```

- [ ] **Step 7: Typecheck and build**

```bash
cd web && npx tsc --noEmit && npm run build
```

Expected: no type errors, Vite build succeeds. A build error referencing `SimDemo` means Step 1 or Step 5 missed a remaining reference — search for `SimDemo` across `web/src` and remove it.

- [ ] **Step 8: Run the existing test suite**

```bash
cd web && npm test
```

Expected: all tests still pass (this task doesn't touch `keyboard.ts`, `gamepad.ts`, `bank.ts`, or `serial.ts`, so their existing coverage is unaffected).

- [ ] **Step 9: Commit**

```bash
git add web/src/App.tsx web/src/styles.css
git commit -m "web: two-tab layout (Loader/Play), remove the old collapsible demo"
```

---

### Task 5: Manual browser verification

**Files:** none (verification only — no code changes expected unless this step surfaces a bug, in which case fix it in the relevant task's file and re-run this checklist).

- [ ] **Step 1: Build and start the dev server**

```bash
cd web
npm run build:sim-wasm
npm run dev
```

- [ ] **Step 2: Loader tab regression check.** Confirm the Loader tab still works exactly as before this plan: connect/disconnect (or at least the UI renders without errors if no device is attached), Add/Upload/Download/Read/Erase buttons present, tour, gamepad-controls-info modal, debug log toggle, sample list drag-drop area. Confirm the `Monitor` icon button and the old collapsible "Try it in your browser" section are gone from this tab.

- [ ] **Step 3: Play tab — desktop browser, landscape-shaped window.**
  - Switch to the Play tab. Confirm the "Play" button screen appears (not an auto-boot).
  - Click Play. Confirm it transitions to "Loading simulator...", then to the full gamepad layout (canvas + D-pad + face buttons + L/R + Select/Start), matching the spec's ASCII layout (D-pad left, screen center, face diamond right, L/R top corners, Select/Start bottom-center).
  - Confirm the canvas shows the firmware's live UI (not a blank/black square) within a few seconds.
  - Click/hold individual on-screen buttons (use the browser's mouse-as-pointer-event support) and confirm the firmware UI responds the same way pressing the equivalent key did in the prior demo.
  - Confirm keyboard input (click the canvas first if needed) and, if a gamepad is available, physical gamepad input still work alongside the touch buttons.
  - Switch back to the Loader tab, then back to Play — confirm it re-shows the "Play" button screen (a fresh instance, not stale state), since `PlayTab`/`usePikoSim` remount when the tab's JSX subtree unmounts/remounts. Confirm no console errors and no runaway `requestAnimationFrame` (check via the same instrumentation approach used in the prior plan's Task 8 if you want strong evidence: patch `window.requestAnimationFrame` to count calls, confirm the count stops increasing after leaving the Play tab).

- [ ] **Step 4: Play tab — mobile viewport emulation, portrait.** Using the browser's device emulation (or an actual phone), load the Play tab in portrait. Confirm the "rotate your phone to play" message shows and the gamepad/Play-button UI is hidden.

- [ ] **Step 5: Play tab — mobile viewport emulation, landscape.** Rotate to landscape (or emulate a landscape mobile viewport, e.g. 812×375). Confirm the "Play" button screen appears, tapping it boots the simulator, and the full gamepad layout fits the viewport without horizontal scrolling. Using touch-emulation (or a real touchscreen), confirm:
  - Tapping and holding a single button works.
  - Holding two buttons at once (e.g. a D-pad direction + a face button, or Select + a face button) works — this is the multi-touch case `TouchButton`'s pointer-ID-set logic exists for.
  - Lifting one finger while another button is still held does not release the still-held button.

- [ ] **Step 6: If everything above checks out, this plan is complete** — no commit needed for this task unless Step 2-5 surfaced a fix, in which case commit that fix in the relevant task's file with a message describing what was wrong.

---

## Self-Review Notes

- **Spec coverage:** navigation structure (Task 4), orientation gate + boot flow (Task 3), touch control layout + multi-touch (Task 2), engine reuse via extracted hook (Task 1), manual verification across desktop/mobile/portrait/landscape (Task 5) — every spec section maps to a task.
- **Type/name consistency checked:** `usePikoSim`'s returned `canvasRef`/`status`/`error`/`start` shape matches exactly what `PlayTab` destructures in Task 3; `GamepadControls`' `maskRef`/`children` props match exactly how `PlayTab` calls it; `BUTTON_BITS.X/Y/A/B` face-button assignment in `GamepadControls` matches `keyboard.ts`'s existing top/right/bottom/left convention verbatim (top=X, right=A, bottom=B, left=Y), not re-derived independently.
- **Reuse verified, not just claimed:** the hook's boot/loop/cleanup body is the existing, already-reviewed `SimDemo.tsx` logic verbatim (only the trigger condition changes, from an unconditional mount effect to an explicit `start()` call) — this plan does not ask anyone to redesign proven code.
