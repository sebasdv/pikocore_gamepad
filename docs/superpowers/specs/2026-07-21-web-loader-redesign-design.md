# Web loader redesign — device-matching visual identity

**Date:** 2026-07-21
**Status:** approved, ready for implementation plan

## Goal

Give the sample-loader web app (`web/`) its own visual identity based on the
Silkscreen pixel typeface and the same monochrome look established for the
GamePi13 device's LCD dashboard this session, instead of the current generic
modern-SaaS look (Inter font, warm cream palette, blue accent links,
rounded corners).

This is a **visual reskin only**. No changes to serial/USB logic, bank
building, audio decoding, or the app's information architecture, beyond one
small content addition (see "Controls reference" below).

## 1. Visual direction: Full Device Skin

The web app's shell should read as the device's dashboard rendered in a
browser, not merely inspired by it:

- Black background, white foreground, everywhere. No light theme.
- Sharp corners (`border-radius: 0`) on every button, panel, input, sample
  row, and the modal — matching the device's blocky UI.
- Thick borders on major containers, replacing today's thin 1px warm-gray
  hairlines: **3px solid white** on top-level panels (the modal, the sample
  list container), **2px solid white** on buttons, inputs, and individual
  sample rows.
- Meters that are currently smooth gradients (capacity meter, transfer
  progress bar) become **segmented/blocky bars** — same visual language as
  the device's stepped parameter bars (a row of solid blocks, lit vs. dim).

## 2. Typography: Silkscreen, everywhere

- Load Silkscreen from Google Fonts:
  `https://fonts.googleapis.com/css2?family=Silkscreen:wght@400;700&display=swap`,
  added as a `<link>` in `web/index.html`.
- `font-family: 'Silkscreen', monospace;` applies app-wide — headings,
  buttons, labels, sample filenames, BPM values, the debug log, the footer.
  Nothing is exempted for this first pass.
- **Known risk, explicitly accepted for now:** Silkscreen is a small pixel
  font; long sample filenames and the debug log's monospace-style output
  may be harder to scan than with the current sans-serif. Decision (made by
  the user): ship everything in Silkscreen first, and only carve out
  exceptions (e.g. keep the debug log or filenames in a plain readable font)
  if real-world legibility turns out to be a problem. Not blocking this pass.

## 3. Color palette: full monochrome, no exceptions

Reuses the exact device palette from `src/gamepi13/ui.cpp`:

| Token | Hex | Device source |
|---|---|---|
| Background | `#000000` | `COL_BG` |
| Foreground / active | `#ffffff` | `COL_WHITE` |
| Muted / inactive | `#666666` | `COL_GRAY` |
| Mid (secondary emphasis) | `#808080` | `COL_GRAY_MID` |
| Dim (unlit segments, subtle borders) | `#404040` | `COL_GRAY_DIM` |
| Panel fill (slightly-off-black surfaces) | `#1a1a1a` | `COL_DARK` |

Today's semantic status colors (`--good` green, `--warn` amber, `--bad` red,
`--accent` blue, `--playhead` red) are **removed entirely**. State is
communicated with intensity/weight/inversion instead of hue, matching how
the device itself dropped color for state (e.g. the retrigger indicator
went from cyan to white this session):

- **Connected / good status** → full white text, solid white left border.
- **Warning status** → white text, `#808080` (mid-gray) left border — one
  step down in emphasis from "good," no inversion.
- **Error / bad status** → **inverted block** (white background, black
  text) instead of red. This is a deliberate, retro-computing-native way to
  say "pay attention" without color — the classic 8-bit terminal error
  convention.
- **Links** (`--accent` today) → white text with an underline; the
  underline (not color) is the affordance that it's a link.
- **Waveform playhead** → white (already matches the device, which also
  uses a plain white playhead line over its monochrome waveform).
- **Capacity/transfer meters** → lit segments white, unlit segments
  `#404040` (dim), exactly like the device's stepped bars. No red
  "over capacity" state color — an over-capacity meter fills every segment
  and the accompanying text flips to the inverted error treatment instead.

## 4. Icons

Keep the existing 14 `lucide-react` icons (Cable, Upload, Download, Play,
Trash2, etc.) as-is, just recolored white-on-black via `currentColor`. No
new custom pixel-icon set for this pass — that's real extra design work
(vendoring ~14 new glyphs) and is out of scope here; flagged as a possible
future follow-up, not part of this redesign.

## 5. Controls reference (new content, existing surface)

Add a compact table of the GamePi13's physical controls to the **existing
help modal** (opened via the "?" / `HelpCircle` button) — not a new
top-level page section, so the main connect/upload/download workflow stays
uncluttered.

- Source: the quick-reference control table already in the project's
  `README.md` (English), not the full Spanish reference in
  `GAMEPI13-INTERFACE.md` (that one is internal/technical detail, not
  end-user-facing).
- Presentation: a simple two-column list (control → function), styled with
  Silkscreen for the button names (`D-PAD`, `SELECT`, `L / R`, `START`,
  etc.) and the existing readable body font for the description column — a
  small, deliberate exception to "everything Silkscreen," justified because
  this is reference text a user needs to actually read quickly, not a
  display label.

## 6. Credits — preserved verbatim

The existing footer content is **not to be changed**, only re-skinned with
the new typography/palette:

> made by [Infinite Digits](https://infinitedigits.co/products/), inspired
> by [MLRws-web](https://github.com/dessertplanet/MLRws-web/)

Both links keep their exact `href` and `title` attributes. This credits the
web loader's own lineage (Infinite Digits / Zack Scholl, and the MLRws-web
project by dessertplanet that this loader was inspired by) — separate from,
and in addition to, the firmware-side acknowledgments already in the
project's main `README.md`.

## 7. Scope boundaries

**In scope:** `web/src/styles.css` (near-total rewrite of the visual
tokens/rules), `web/index.html` (font `<link>`), targeted JSX changes in
`web/src/App.tsx` for the new controls-reference content inside the help
modal, and the `driver.js` tour popover styles (`.driver-popover.pikocore-tour*`
in `styles.css`) get the same monochrome/Silkscreen treatment for
consistency with the rest of the help experience.

**Out of scope:** serial/USB connection logic, bank-building/audio-decoding
logic (`audio.ts`, `bank.ts`, `serial.ts`), the app's overall information
architecture (toolbar/capacity/debug-log/sample-list/footer stay in their
current order and grouping), and any new custom icon set.

## 8. Process

Design locally first (this app already builds and runs via `npm run dev`),
verify visually against real content (long filenames, an empty state, an
error state, the help modal open) before publishing. Publish by pushing to
`main`, which the existing `deploy-web.yml` workflow already picks up
automatically.
