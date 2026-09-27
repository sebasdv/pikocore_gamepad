# Web Loader Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `web/` (the pikocore sample loader) the same monochrome, Silkscreen-typeset visual identity as the GamePi13 device's LCD dashboard, per `docs/superpowers/specs/2026-07-21-web-loader-redesign-design.md`.

**Architecture:** Pure reskin. Remove the light/dark theme system (single dark-only look from now on), rewrite `web/src/styles.css` against the device's exact monochrome palette, and add one small new piece of content — a device-controls reference modal — reusing the existing `.info-modal`/`.modal-backdrop` CSS pattern already used by the ittybittymidi help popup. No changes to serial/USB logic, bank building, or audio decoding.

**Tech Stack:** React + TypeScript + Vite (existing), Google Fonts (Silkscreen), plain CSS custom properties (no new libraries).

---

## Important correction vs. the spec

The spec says the controls reference goes "in the existing help modal." There is **no existing static help modal** — the "?" (`HelpCircle`) button in the toolbar launches the `driver.js` guided tour (`startTour()`), not a modal. Building the controls reference into that would mean hijacking an existing, working feature (the tour) to do something unrelated, which conflicts with the spec's own scope boundary ("no changes to... the app's information architecture, beyond one small content addition").

This plan instead adds a **second small icon button** (a `Gamepad2` icon, confirmed available in the installed `lucide-react` version) right next to the "?" tour button, opening a **new** modal built with the exact same `.info-modal`/`.modal-backdrop` markup pattern already used by the ittybittymidi popup. The tour stays completely untouched. This is the smallest change that satisfies "controls reference, reachable from a help-adjacent icon, not cluttering the main workflow."

---

## File Structure

- Modify: `web/index.html` — add the Silkscreen Google Fonts `<link>`.
- Modify: `web/src/App.tsx` — remove the theme system; add the controls-reference modal + its trigger button; one JSX class-name hook for the over-capacity state.
- Modify: `web/src/styles.css` — full rewrite of visual tokens/rules (palette, shapes, borders, status colors, meters, tour popover, footer). No new files — the new modal reuses existing `.info-modal` classes.

---

### Task 1: Load Silkscreen, remove the light/dark theme system

**Files:**
- Modify: `web/index.html`
- Modify: `web/src/App.tsx`

- [ ] **Step 1: Add the Silkscreen font link**

In `web/index.html`, add the font `<link>` inside `<head>`, right after the `viewport` meta tag:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Silkscreen:wght@400;700&display=swap" rel="stylesheet" />
    <title>pikocore loader</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: Remove the `Theme` type and the read-only `theme` state**

In `web/src/App.tsx`, delete this line (around line 62):

```typescript
type Theme = 'light' | 'dark';
```

Delete this line (around line 93):

```typescript
  const [theme] = useState<Theme>(() => loadTheme());
```

- [ ] **Step 3: Remove the effect that persists theme to localStorage**

Delete this block (around lines 105-107):

```typescript
  useEffect(() => {
    window.localStorage.setItem('pikocore-theme', theme);
  }, [theme]);
```

- [ ] **Step 4: Delete the `loadTheme()` function**

At the end of the file (around lines 1271-1276), delete:

```typescript
function loadTheme(): Theme {
  const stored =
    window.localStorage.getItem('pikocore-theme') ?? window.localStorage.getItem('pikocore-theme');
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}
```

- [ ] **Step 5: Drop the `data-theme` attribute on the root element**

Change (around line 766):

```tsx
    <main className="app" data-theme={theme}>
```

to:

```tsx
    <main className="app">
```

- [ ] **Step 6: Simplify the tour's `popoverClass` to a fixed string**

Change (around line 679):

```typescript
      popoverClass: `pikocore-tour pikocore-tour-${theme}`,
```

to:

```typescript
      popoverClass: 'pikocore-tour',
```

- [ ] **Step 7: Drop the `theme` prop from the `SampleRow` call site**

Find the JSX where `SampleRow` is rendered (around line 1041-1045):

```tsx
              playing={playingId === sample.id}
              playheadFrame={playingId === sample.id ? playheadFrame : null}
              theme={theme}
              onUpdate={(patch) => updateSample(sample.id, patch)}
              onRemove={() => removeSample(sample.id)}
```

Remove the `theme={theme}` line:

```tsx
              playing={playingId === sample.id}
              playheadFrame={playingId === sample.id ? playheadFrame : null}
              onUpdate={(patch) => updateSample(sample.id, patch)}
              onRemove={() => removeSample(sample.id)}
```

- [ ] **Step 8: Drop `theme` from the `SampleRow` component signature**

Find the `SampleRow` function parameters (around lines 1070-1084):

```tsx
  playing,
  playheadFrame,
  theme,
  onUpdate,
  onRemove,
```

```tsx
  playing: boolean;
  playheadFrame: number | null;
  theme: Theme;
  onUpdate: (patch: Partial<BankSample>) => void;
  onRemove: () => void;
```

Remove both `theme` lines, leaving:

```tsx
  playing,
  playheadFrame,
  onUpdate,
  onRemove,
```

```tsx
  playing: boolean;
  playheadFrame: number | null;
  onUpdate: (patch: Partial<BankSample>) => void;
  onRemove: () => void;
```

- [ ] **Step 9: Drop the `theme` prop from the `<Waveform>` call site**

Change (around line 1126):

```tsx
      <Waveform sample={sample} playheadFrame={playheadFrame} theme={theme} />
```

to:

```tsx
      <Waveform sample={sample} playheadFrame={playheadFrame} />
```

- [ ] **Step 10: Drop `theme` from the `Waveform` component signature and hardcode its colors**

Find the `Waveform` function (around lines 1155-1162):

```tsx
  sample,
  playheadFrame,
  theme,
}: {
  sample: BankSample;
  playheadFrame: number | null;
  theme: Theme;
}) {
```

Replace with:

```tsx
  sample,
  playheadFrame,
}: {
  sample: BankSample;
  playheadFrame: number | null;
}) {
```

- [ ] **Step 11: Hardcode the waveform's drawing colors to the device palette**

In the `draw()` function inside `Waveform` (around lines 1176-1177), change:

```typescript
    const waveBackground = theme === 'dark' ? '#191918' : '#f7f7f4';
    const waveLine = theme === 'dark' ? '#f1f0ea' : '#202020';
```

to:

```typescript
    const waveBackground = '#000000';
    const waveLine = '#ffffff';
```

And a few lines down (around line 1202), change:

```typescript
      ctx.fillStyle = theme === 'dark' ? '#ff7667' : '#d23b2a';
```

to:

```typescript
      ctx.fillStyle = '#ffffff';
```

- [ ] **Step 12: Drop `theme` from the `useEffect` dependency array**

Change (around line 1209):

```typescript
  }, [sample, playheadFrame, theme]);
```

to:

```typescript
  }, [sample, playheadFrame]);
```

- [ ] **Step 13: Build to confirm no TypeScript errors**

Run: `cd web && npm run build`
Expected: builds cleanly with no `Theme`/`theme`-related type errors. (Vite's build already ran `tsc` first per the existing `"build": "tsc && vite build"` script — a leftover reference to `Theme` or `theme` will fail this step.)

- [ ] **Step 14: Commit**

```bash
cd /c/pikocore-main
git add web/index.html web/src/App.tsx
git commit -m "feat(web): load Silkscreen font, remove light/dark theme (dark-only from now on)"
```

---

### Task 2: Rewrite styles.css — monochrome palette, sharp shapes, blocky meters

**Files:**
- Modify: `web/src/styles.css` (full replacement)

- [ ] **Step 1: Replace the entire file content**

Replace the full contents of `web/src/styles.css` with:

```css
.app {
  color-scheme: dark;
  --page: #000000;
  --text: #ffffff;
  --muted: #808080;
  --muted-2: #666666;
  --panel: #1a1a1a;
  --control: #000000;
  --border: #404040;
  --border-strong: #ffffff;
  --meter: #404040;
  --primary: #ffffff;
  --primary-text: #000000;
  --debug-bg: #000000;
  --debug-text: #ffffff;
  --debug-title: #808080;
  font-family: 'Silkscreen', monospace;
  color: var(--text);
  background: var(--page);
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px;
}

.app,
.app * {
  box-sizing: border-box;
}

.app button,
.app .button,
.app input,
.app select {
  font: inherit;
}

.app button,
.app .button,
.app select {
  height: 34px;
  border: 2px solid var(--border-strong);
  background: var(--control);
  color: var(--text);
  border-radius: 0;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
  text-decoration: none;
}

.app button.primary {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--primary-text);
}

.app .button.primary {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--primary-text);
}

.app button.needs-sync {
  background: var(--muted);
  border-color: var(--muted);
  color: #000000;
}

.app button:disabled,
.app .button.disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.app .button input {
  display: none;
}

.app select {
  min-width: 132px;
  padding: 0 28px 0 9px;
}

.app select.default-firmware {
  border-color: var(--primary);
  box-shadow: inset 3px 0 0 var(--primary);
  font-weight: 700;
}

.app .topbar {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
}

.app h1 {
  margin: 0 0 8px;
  font-size: 24px;
  line-height: 1;
  letter-spacing: 1px;
}

.app .status {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-left: 4px solid var(--muted-2);
  padding: 0 10px;
  color: var(--muted);
}

.app .spinner {
  width: 14px;
  height: 14px;
  flex: 0 0 14px;
  border: 2px solid var(--border-strong);
  border-top-color: var(--muted);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Good: full white text + border -- brightest state, matches the device's
   "lit" convention. */
.app .status.good {
  border-color: var(--text);
  color: var(--text);
}

/* Warn: one step down from "good" -- mid-gray border, text stays legible
   white. No hue is used to distinguish it, only the border's intensity. */
.app .status.warn {
  border-color: var(--muted);
}

/* Bad: inverted block (white background, black text) instead of red --
   the classic monochrome-terminal way to say "pay attention" without color. */
.app .status.bad {
  border-color: var(--text);
  background: var(--text);
  color: #000000;
  padding: 0 10px;
}

.app .toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-start;
}

.app .firmware-download {
  display: inline-flex;
  gap: 6px;
}

.app .toolbar-subrow {
  display: flex;
  justify-content: flex-start;
  margin-top: -2px;
}

.app .clock-mode {
  height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--muted);
  font-size: 13px;
  white-space: nowrap;
}

.app .clock-mode label {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.app .clock-mode input {
  width: 16px;
  height: 16px;
  accent-color: var(--text);
}

.app .clock-mode .disabled {
  opacity: 0.45;
}

/* Links: no color left to lean on -- the underline is the affordance. */
.app .text-button {
  height: auto;
  border: 0;
  background: transparent;
  color: var(--text);
  padding: 0;
  font-size: inherit;
  text-decoration: underline;
}

.app .text-button:hover {
  text-decoration: none;
}

.app .clock-mode a {
  color: var(--text);
  text-decoration: underline;
}

.app .clock-mode a:hover {
  text-decoration: none;
}

.app .icon-button {
  width: 34px;
  padding: 0;
  justify-content: center;
}

.app .icon-button[aria-pressed="true"] {
  border-color: var(--text);
  background: var(--text);
  color: #000000;
}

.app .firmware-warning {
  margin: 14px 0 0;
  border: 2px solid var(--border-strong);
  border-left: 4px solid var(--muted);
  border-radius: 0;
  background: var(--panel);
  color: var(--text);
  padding: 12px 14px;
}

.app .firmware-warning strong {
  display: block;
  margin-bottom: 5px;
}

.app .firmware-warning p {
  margin: 4px 0 0;
  color: var(--muted);
}

.app .capacity {
  margin: 22px 0 14px;
}

/* Over capacity: no red -- the whole capacity line flips to the same
   inverted block used by .status.bad. */
.app .capacity.over-capacity .capacity-line {
  background: var(--text);
  color: #000000;
  padding: 4px 8px;
}

.app .modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: 22px;
  background: rgb(0 0 0 / 0.75);
}

.app .modal-close {
  justify-self: end;
}

.driver-popover.pikocore-tour {
  width: min(340px, calc(100vw - 32px));
  max-width: min(340px, calc(100vw - 32px));
  border: 2px solid #ffffff;
  border-radius: 0;
  background: #000000;
  color: #ffffff;
  padding: 14px;
  box-shadow: 0 18px 48px rgb(0 0 0 / 0.5);
}

.driver-popover.pikocore-tour .driver-popover-title {
  padding-right: 28px;
  font: 700 16px/1.25 'Silkscreen', monospace;
  letter-spacing: 1px;
}

.driver-popover.pikocore-tour .driver-popover-description {
  color: #808080;
  font: 14px/1.45 Inter, ui-sans-serif, system-ui, sans-serif;
}

.driver-popover.pikocore-tour .driver-popover-description p {
  margin: 8px 0 0;
}

.driver-popover.pikocore-tour .tour-pikocore {
  display: block;
  width: 100%;
  max-height: min(42vh, 260px);
  object-fit: contain;
  border: 2px solid #ffffff;
  border-radius: 0;
  background: transparent;
}

.driver-popover.pikocore-tour .driver-popover-close-btn {
  top: 8px;
  right: 8px;
  color: #808080;
}

.driver-popover.pikocore-tour .driver-popover-close-btn:hover,
.driver-popover.pikocore-tour .driver-popover-close-btn:focus {
  color: #ffffff;
}

.driver-popover.pikocore-tour .driver-popover-footer {
  margin-top: 14px;
}

.driver-popover.pikocore-tour .driver-popover-progress-text {
  color: #808080;
  font: 13px/1 'Silkscreen', monospace;
}

.driver-popover.pikocore-tour .driver-popover-footer button {
  height: 30px;
  border: 2px solid #ffffff;
  border-radius: 0;
  background: #000000;
  color: #ffffff;
  padding: 0 10px;
  font: 13px/1 'Silkscreen', monospace;
  text-shadow: none;
}

.driver-popover.pikocore-tour .driver-popover-footer .driver-popover-next-btn {
  border-color: #ffffff;
  background: #ffffff;
  color: #000000;
}

.driver-popover.pikocore-tour .driver-popover-arrow {
  border-color: #000000;
}

.driver-popover.pikocore-tour .driver-popover-arrow-side-left {
  border-right-color: transparent;
  border-bottom-color: transparent;
  border-top-color: transparent;
}

.driver-popover.pikocore-tour .driver-popover-arrow-side-right {
  border-left-color: transparent;
  border-bottom-color: transparent;
  border-top-color: transparent;
}

.driver-popover.pikocore-tour .driver-popover-arrow-side-top {
  border-right-color: transparent;
  border-bottom-color: transparent;
  border-left-color: transparent;
}

.driver-popover.pikocore-tour .driver-popover-arrow-side-bottom {
  border-left-color: transparent;
  border-top-color: transparent;
  border-right-color: transparent;
}

.app .info-modal {
  width: min(720px, 100%);
  max-height: calc(100vh - 44px);
  display: grid;
  gap: 12px;
  overflow: auto;
  border: 3px solid var(--border-strong);
  border-radius: 0;
  background: var(--panel);
  padding: 12px;
}

.app .info-modal img {
  display: block;
  width: 100%;
  max-height: 56vh;
  object-fit: contain;
  border: 2px solid var(--border-strong);
  border-radius: 0;
  background: var(--control);
}

.app .info-modal-copy {
  display: grid;
  gap: 8px;
}

.app .info-modal-copy h2,
.app .info-modal-copy p {
  margin: 0;
}

.app .info-modal-copy h2 {
  font-size: 18px;
  line-height: 1.2;
  letter-spacing: 1px;
}

.app .info-modal-copy p {
  color: var(--muted);
  line-height: 1.45;
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
}

.app .info-modal-copy a {
  color: var(--text);
  text-decoration: underline;
}

/* Device controls reference table (help modal) */
.app .controls-table {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 8px 16px;
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  font-size: 13px;
}

.app .controls-table dt {
  font-family: 'Silkscreen', monospace;
  color: var(--text);
  white-space: nowrap;
}

.app .controls-table dd {
  margin: 0;
  color: var(--muted);
}

.app .capacity-line {
  display: grid;
  grid-template-columns: repeat(4, max-content);
  gap: 18px;
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 7px;
}

.app .meter,
.app .transfer {
  height: 8px;
  background: var(--meter);
  overflow: hidden;
  border-radius: 0;
}

/* Segmented/blocky fill -- a repeating stripe pattern instead of a solid
   color, echoing the device's stepped parameter bars (6px lit block, 2px
   gap) without needing to compute a discrete segment count in JS. */
.app .meter div,
.app .transfer {
  height: 100%;
  background-color: var(--text);
  background-image: repeating-linear-gradient(
    to right,
    var(--text) 0px,
    var(--text) 6px,
    var(--page) 6px,
    var(--page) 8px
  );
}

.app .meter div.over {
  background-color: var(--text);
  background-image: repeating-linear-gradient(
    to right,
    var(--text) 0px,
    var(--text) 6px,
    var(--page) 6px,
    var(--page) 8px
  );
}

.app .transfer-detail {
  margin-top: 6px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.3;
}

.app .sample-list {
  display: grid;
  gap: 10px;
  min-height: 280px;
  padding-bottom: 24px;
}

.app .site-footer {
  padding: 6px 0 18px;
  color: var(--muted);
  font-size: 13px;
}

.app .site-footer a {
  color: var(--text);
  text-decoration: underline;
}

.app .site-footer a:hover {
  text-decoration: none;
}

.app .debug-log {
  margin: 0 0 14px;
  padding: 10px;
  border: 2px solid var(--border-strong);
  background: var(--debug-bg);
  color: var(--debug-text);
  font-family: 'Silkscreen', monospace;
  font-size: 12px;
  line-height: 1.4;
}

.app .debug-title {
  color: var(--debug-title);
  margin-bottom: 4px;
}

.app .debug-output {
  display: block;
  width: 100%;
  height: 150px;
  margin: 0;
  padding: 0;
  resize: vertical;
  border: 0;
  outline: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  line-height: inherit;
  white-space: pre;
}

.app .debug-empty {
  color: var(--muted-2);
}

.app .empty {
  min-height: 260px;
  border: 2px dashed var(--border-strong);
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 10px;
  color: var(--muted-2);
}

.app .sample-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  border: 2px solid var(--border);
  background: var(--panel);
  border-radius: 0;
  padding: 10px;
}

.app .sample-meta {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: 32px minmax(160px, 1fr) max-content;
  align-items: center;
  gap: 10px;
  color: var(--muted);
  font-size: 13px;
}

.app .sample-stats {
  display: grid;
  grid-template-columns: repeat(4, max-content);
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}

.app .slot {
  display: inline-grid;
  place-content: center;
  height: 26px;
  width: 26px;
  border-radius: 0;
  background: var(--primary);
  color: var(--primary-text);
}

.app .name,
.app .bpm {
  height: 30px;
  border: 2px solid var(--border);
  border-radius: 0;
  background: var(--control);
  color: var(--text);
  padding: 0 8px;
}

.app .name {
  width: 100%;
}

.app .bpm {
  width: 82px;
  margin-left: 6px;
}

.app .waveform {
  width: 100%;
  height: 92px;
  border: 2px solid var(--border);
  border-radius: 0;
  background: #000000;
}

.app .row-actions {
  display: grid;
  grid-template-columns: repeat(4, 34px);
  gap: 6px;
}

.app .row-actions button {
  width: 34px;
  padding: 0;
  justify-content: center;
}

@media (max-width: 760px) {
  .app .topbar,
  .app .sample-row {
    grid-template-columns: 1fr;
    display: grid;
  }

  .app .toolbar {
    width: 100%;
    justify-content: flex-start;
  }

  .app .sample-meta {
    grid-template-columns: 32px minmax(0, 1fr);
  }

  .app .capacity-line {
    grid-template-columns: 1fr 1fr;
  }

  .app .sample-meta .name {
    grid-column: 2;
  }

  .app .sample-stats {
    grid-column: 1 / -1;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) max-content max-content;
    gap: 6px;
    font-size: 12px;
  }

  .app .sample-stats .bpm {
    width: 58px;
    margin-left: 4px;
  }

  .app .row-actions {
    grid-template-columns: repeat(4, 34px);
  }
}
```

- [ ] **Step 2: Add the over-capacity class hook**

In `web/src/App.tsx`, find the capacity section (around line 973):

```tsx
      <section className="capacity">
```

Change to:

```tsx
      <section className={overCapacity ? 'capacity over-capacity' : 'capacity'}>
```

- [ ] **Step 3: Build to confirm no errors**

Run: `cd web && npm run build`
Expected: builds cleanly.

- [ ] **Step 4: Commit**

```bash
cd /c/pikocore-main
git add web/src/styles.css web/src/App.tsx
git commit -m "feat(web): monochrome device palette, sharp shapes, blocky meters, no semantic color"
```

---

### Task 3: Add the device controls reference modal

**Files:**
- Modify: `web/src/App.tsx`

- [ ] **Step 1: Import the `Gamepad2` icon**

Change the `lucide-react` import block (lines 1-16) from:

```typescript
import {
  ArrowDown,
  ArrowUp,
  Cable,
  Download,
  Eraser,
  FolderOpen,
  HardDrive,
  Pause,
  Play,
  Plus,
  HelpCircle,
  Terminal,
  Trash2,
  Upload,
} from 'lucide-react';
```

to:

```typescript
import {
  ArrowDown,
  ArrowUp,
  Cable,
  Download,
  Eraser,
  FolderOpen,
  Gamepad2,
  HardDrive,
  Pause,
  Play,
  Plus,
  HelpCircle,
  Terminal,
  Trash2,
  Upload,
} from 'lucide-react';
```

- [ ] **Step 2: Add the modal's open/close state**

Change (around line 92):

```typescript
  const [ittybittymidiInfoOpen, setIttybittymidiInfoOpen] = useState(false);
```

to:

```typescript
  const [ittybittymidiInfoOpen, setIttybittymidiInfoOpen] = useState(false);
  const [controlsInfoOpen, setControlsInfoOpen] = useState(false);
```

- [ ] **Step 3: Add the trigger button next to the tour button**

Find the tour button (around lines 876-883):

```tsx
          <button
            className="icon-button"
            onClick={startTour}
            title="Show pikocore tour"
            aria-label="Show pikocore tour"
          >
            <HelpCircle size={18} />
          </button>
```

Add a new button right after it:

```tsx
          <button
            className="icon-button"
            onClick={startTour}
            title="Show pikocore tour"
            aria-label="Show pikocore tour"
          >
            <HelpCircle size={18} />
          </button>
          <button
            className="icon-button"
            onClick={() => setControlsInfoOpen(true)}
            title="Show pikocore gamepad controls"
            aria-label="Show pikocore gamepad controls"
          >
            <Gamepad2 size={18} />
          </button>
```

- [ ] **Step 4: Add the modal JSX**

Find the ittybittymidi modal's closing (around lines 941-971, ending with `)}` right before `<section className="capacity">` or `<section className={overCapacity ...`). Add the new modal directly after that ittybittymidi modal's `)} ` closing and before the capacity section:

```tsx
      {controlsInfoOpen ? (
        <div className="modal-backdrop" role="presentation" onClick={() => setControlsInfoOpen(false)}>
          <div
            className="info-modal"
            role="dialog"
            aria-modal="true"
            aria-label="pikocore gamepad controls"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="info-modal-copy">
              <h2>pikocore gamepad controls</h2>
              <dl className="controls-table">
                <dt>D-pad + Y/X/B/A</dt>
                <dd>pikocore's 8 music buttons</dd>
                <dt>Select</dt>
                <dd>cycle parameter mode (tap), or hold + a music button to jump directly to that mode</dd>
                <dt>L / R</dt>
                <dd>decrease/increase the active parameter (Function A); hold to repeat</dd>
                <dt>Start (tap)</dt>
                <dd>mute / start-stop</dd>
                <dt>Start (hold) + L/R</dt>
                <dd>edit Function B instead of Function A</dd>
                <dt>Up+Down+B+A</dt>
                <dd>reset FX (filter, distortion, all probabilities)</dd>
                <dt>Down+Left+X+B</dt>
                <dd>toggle clock lock</dd>
              </dl>
            </div>
            <button
              className="modal-close"
              onClick={() => setControlsInfoOpen(false)}
              title="Close controls reference"
              aria-label="Close controls reference"
            >
              Close
            </button>
          </div>
        </div>
      ) : null}
```

- [ ] **Step 5: Build to confirm no errors**

Run: `cd web && npm run build`
Expected: builds cleanly.

- [ ] **Step 6: Commit**

```bash
cd /c/pikocore-main
git add web/src/App.tsx
git commit -m "feat(web): add pikocore gamepad controls reference modal"
```

---

### Task 4: Visual verification and credits check

**Files:** none (verification only)

- [ ] **Step 1: Start the dev server and open it**

Run (or use the project's preview tooling): `cd web && npm run dev`, open `http://localhost:5173`.

- [ ] **Step 2: Verify the base look**

Confirm: black background, white Silkscreen text throughout, sharp corners on every button/panel/input, thick white borders, no light-mode flash on load, and that all 14 lucide-react icons (Cable, Upload, Download, Play, Trash2, etc.) render white-on-black via inherited `currentColor` -- no separate icon-recoloring step was needed since Task 2's palette change alone should carry them, but confirm none render in a stale color.

- [ ] **Step 3: Verify status states**

Trigger (or inspect via React state / by reading the code paths) all three status kinds:
- `good` (e.g. after a successful connect) — full white text + border.
- `warn` (e.g. "Firmware update required") — mid-gray (`#808080`) border, white text.
- `bad` (e.g. a caught error) — inverted block, white background, black text.

Confirm none of them render green/amber/red.

- [ ] **Step 4: Verify the capacity meter**

Load enough samples to approach and then exceed device capacity. Confirm the meter fill shows the blocky/striped pattern (not a solid gradient), and that exceeding capacity flips the `.capacity-line` to the inverted block (no red).

- [ ] **Step 5: Verify the new controls modal**

Click the new gamepad-icon button next to the "?" tour button. Confirm the modal opens with the 7-row controls table, Silkscreen on the left column (control names) and readable Inter on the right column (descriptions), and that it closes via the Close button and via clicking the backdrop.

- [ ] **Step 6: Verify the tour still works**

Click "?" (`HelpCircle`). Confirm the guided tour still launches normally with the new monochrome popover styling (`pikocore-tour` class), and that its Next/Back/Done buttons and progress text are legible.

- [ ] **Step 7: Verify the footer credits are unchanged**

Confirm the footer still reads "made by Infinite Digits, inspired by MLRws-web" with both links pointing to `https://infinitedigits.co/products/` and `https://github.com/dessertplanet/MLRws-web/` respectively (view source or inspect the DOM — the text/`href`s must be byte-identical to before this redesign, only the visual styling changed).

- [ ] **Step 8: Verify a long sample filename and the debug log**

Add a sample with a long filename and open the debug log (the `Terminal` icon toggle). Per the spec's accepted risk, check whether Silkscreen is legible enough at these sizes. If it's genuinely hard to read, note it for a follow-up (do not silently change scope here — the spec explicitly deferred this decision).

- [ ] **Step 9: Stop the dev server, confirm a clean production build**

Run: `cd web && npm run build`
Expected: succeeds, no errors.

- [ ] **Step 10: Report findings**

Summarize what was checked in steps 2-8 and flag anything from Step 8 that looked hard to read, before considering this ready to publish (publishing itself — pushing to `main` — is a separate, explicit step for the user per this project's established workflow).
