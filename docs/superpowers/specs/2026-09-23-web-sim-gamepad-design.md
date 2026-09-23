# Virtual gamepad "Play" tab — design

## Goal

Turn the existing in-browser pikocore simulator demo (a collapsible section in
the web loader, added in [2026-09-23-web-sim-demo-design.md](2026-09-23-web-sim-demo-design.md))
into a full mobile-first "Play" tab: a dedicated screen where the loader acts
as a virtual pikocore gamepad, with on-screen touch controls arranged like
the real GamePi13's physical layout, alongside the keyboard and physical
Gamepad API support that already exist.

Non-goals: controlling a real, physically-connected pikocore device (this
stays a browser-only simulation, same as the existing demo); portrait-mode
gamepad layout (landscape-only, with a rotate prompt in portrait); any change
to the underlying WASM/audio engine, `PikoSim`, keyboard mapping, gamepad
mapping, or the AudioWorklet — all of that is reused unchanged.

## Architecture

`web/src/App.tsx` moves from a single-screen layout to two tabs, tracked
with plain React state (`const [tab, setTab] = useState<'loader' | 'play'>`)
— no routing library, since there are only two views and no need for
per-tab URLs yet.

- **Loader tab**: everything that exists today (connect, upload/download
  bank, samples, firmware, tour, debug log). The `Monitor` toggle button and
  the collapsible `sim-demo-section` are removed from here — that
  functionality moves into the Play tab.
- **Play tab**: the new mobile-first virtual gamepad screen.

The tab switcher sits at the top, below the header — two tab buttons in the
same monochrome visual language as the rest of the app (white border =
active, gray = inactive, no rounded corners).

## Play tab: orientation and boot flow

**Orientation gate**: the Play tab is designed for landscape only. In
portrait (a media query on `orientation: portrait`), instead of attempting a
second stacked-layout design, the tab shows a simple "rotate your phone to
play" screen with an icon and one line of text. No duplicate CSS layout for
portrait controls.

**Boot flow** (landscape only):
1. Before tapping "Play": a simple screen — title, one line of description,
   a large "Play" button. Nothing is downloaded yet.
2. Tap "Play": that same tap synchronously creates/resumes the
   `AudioContext` (satisfies the user-gesture requirement — the same fix
   already applied defensively on keydown/pointerdown in the prior demo
   carries over as a second line of defense, but this button tap is now the
   primary, reliable gesture). `PikoSim.create()` starts; a "Loading..."
   state shows while the WASM (~185KB) and the demo bank (~2MB) download and
   the module boots.
3. Success: the full gamepad layout appears (screen + D-pad + face buttons
   + L/R + Select/Start).
4. Error: the same inverted-block error style already established
   (`.status.bad` / `.sim-demo-error`'s pattern) — real failure message, no
   generic text.

## Play tab: gamepad layout

Recreates the GamePi13's physical control arrangement (per
[GAMEPI13-INTERFACE.md](../../../GAMEPI13-INTERFACE.md)'s button map and the
existing demo's `sim/README.md` button table), in the loader's existing
monochrome visual language — not a skeuomorphic recreation of the device's
plastic body.

```
┌─[L]──────────────────────────────[R]─┐
│                                       │
│   ↑                    ┌───────┐  Y  │
│ ← ┼ →     ┌──────┐     │ SCREEN│ X  B│
│   ↓       │SELECT│START│ 240px │  A  │
│           └──────┘     └───────┘     │
└───────────────────────────────────────┘
```

- **Center**: the LCD canvas (240×240), scaled with `object-fit: contain` to
  fill available height without distortion, `image-rendering: pixelated`.
- **Left**: D-pad — a cross of 4 touch buttons (Up/Down/Left/Right).
- **Right**: a diamond of 4 face buttons, using the same position-based
  mapping `keyboard.ts` already uses (top=X, right=A, bottom=B, left=Y) —
  same labels the physical device prints, in the same positions.
- **Top corners**: L and R shoulder buttons.
- **Bottom-center, between the D-pad and the screen**: Select and Start,
  smaller than the main buttons.

**Multi-touch**: every button is its own element using `onPointerDown` /
`onPointerUp` / `onPointerCancel` (not `onClick`, which doesn't support
press-and-hold or multi-button combos). Pointer Events handle multiple
simultaneous fingers natively — each button tracks its own pressed state
independently, no custom touch-tracking logic needed. This is required
because several real-device combos (Select+music button, Start+L/R, two face
buttons at once) need more than one button held down at the same time.

**Input fan-in**: touch, physical Gamepad API, and keyboard all write into
the same button mask, merged once per animation frame — exactly the pattern
the existing demo already uses for keyboard+gamepad (see `SimDemo.tsx`'s
`tick()`), extended with a third source.

## Reused unchanged

`PikoSim` (`simModule.ts`), `keyToButtonBit`/`BUTTON_BITS` (`keyboard.ts`),
`pollGamepadMask` (`gamepad.ts`), and the `AudioWorklet`
(`sim-audio-worklet.js`, including its queue-depth-reporting pacing fix) are
reused without modification.

## File structure

```
web/src/sim/usePikoSim.ts       new — extracts the boot/rAF-loop/cleanup logic
                                  that currently lives inline in SimDemo.tsx's
                                  useEffect into a reusable hook; exposes
                                  canvasRef, status, error, start(), and a
                                  button-mask setter that keyboard/gamepad/touch
                                  all feed into
web/src/sim/GamepadControls.tsx  new — D-pad, X/Y/B/A diamond, L/R,
                                  Select/Start as touch buttons (Pointer
                                  Events), laid out to match the physical
                                  device's arrangement
web/src/sim/PlayTab.tsx          new — the whole tab: orientation gate, the
                                  "Play" button gate, and once loaded, the
                                  canvas + GamepadControls + keyboard/physical-
                                  gamepad input wiring
web/src/sim/SimDemo.tsx          removed — its logic is split between
                                  usePikoSim.ts and PlayTab.tsx; there is no
                                  separate small/collapsed version anymore
web/src/App.tsx                  modified — tab state, tab switcher UI,
                                  removes the Monitor button and
                                  sim-demo-section, renders <PlayTab /> when
                                  the active tab is "play"
web/src/styles.css               modified — tab switcher styles, the
                                  landscape gamepad grid layout, the "rotate
                                  your phone" screen, the "Play" button screen
```

`keyboard.ts`, `gamepad.ts`, `simModule.ts`, and `sim-audio-worklet.js` are
not touched.

## Testing

Manual verification in the browser, same approach as the prior demo's Task
8: load the Play tab, confirm the rotate prompt appears in portrait and the
gamepad appears in landscape, tap "Play" and confirm boot succeeds, confirm
every touch button (including two-finger combos) reaches the firmware the
same way the keyboard mapping already does, confirm physical
gamepad/keyboard input still work alongside touch, confirm leaving the Play
tab tears down audio/rendering cleanly (reusing the teardown logic already
verified for the prior demo). No new automated browser test suite — the
existing `keyboard.test.ts` coverage stays valid since `keyboard.ts` isn't
touched.

## Out of scope for this pass

- Portrait-mode gamepad layout (rotate-prompt only)
- Sending input to a real, physically-connected pikocore device
- Any change to WASM/audio pacing, `PikoSim`, or the AudioWorklet beyond
  what's already shipped
- Haptic feedback, sound effects for touch button presses, or any polish
  beyond functional parity with keyboard/gamepad input
