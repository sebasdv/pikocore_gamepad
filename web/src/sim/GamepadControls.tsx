import { useRef } from 'react';
import { BUTTON_BITS } from './keyboard';
import { DirectionalCluster } from './DirectionalCluster';

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
  const buttonRef = useRef<HTMLButtonElement | null>(null);

  // :active is unreliable on iOS for custom elements (Safari often withholds it without a
  // touchstart handler / sufficient delay), so drive the pressed visual explicitly off the
  // same pointer set that already tracks held pointers, via a data attribute.
  const syncPressedAttr = () => {
    if (pointersRef.current.size > 0) {
      buttonRef.current?.setAttribute('data-pressed', 'true');
    } else {
      buttonRef.current?.removeAttribute('data-pressed');
    }
  };

  const press = (pointerId: number) => {
    pointersRef.current.add(pointerId);
    maskRef.current |= bit;
    syncPressedAttr();
  };
  const release = (pointerId: number) => {
    pointersRef.current.delete(pointerId);
    if (pointersRef.current.size === 0) maskRef.current &= ~bit;
    syncPressedAttr();
  };

  return (
    <button
      ref={buttonRef}
      type="button"
      className={`gamepad-btn ${className}`}
      onPointerDown={(event) => {
        event.preventDefault();
        (event.target as Element).setPointerCapture(event.pointerId);
        press(event.pointerId);
      }}
      onPointerUp={(event) => release(event.pointerId)}
      onPointerCancel={(event) => release(event.pointerId)}
      onContextMenu={(event) => event.preventDefault()}
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
  // Each side column stacks a shoulder button (top), Select/Start (mid-height) and the cross
  // (bottom), so the screen in the middle gets the full height of the viewport.
  return (
    <div className="play-gamepad">
      <div className="play-gamepad-side play-gamepad-left">
        <TouchButton bit={BUTTON_BITS.L} maskRef={maskRef} label="L" className="gamepad-shoulder-btn side-top" />
        <TouchButton bit={BUTTON_BITS.SELECT} maskRef={maskRef} label="Select" className="gamepad-center-btn side-mid" />
        <DirectionalCluster
          maskRef={maskRef}
          ariaLabel="D-pad"
          className="side-bottom gamepad-dpad"
          bits={{ up: BUTTON_BITS.UP, down: BUTTON_BITS.DOWN, left: BUTTON_BITS.LEFT, right: BUTTON_BITS.RIGHT }}
        />
      </div>
      <div className="play-gamepad-screen">{children}</div>
      <div className="play-gamepad-side play-gamepad-right">
        <TouchButton bit={BUTTON_BITS.R} maskRef={maskRef} label="R" className="gamepad-shoulder-btn side-top" />
        <TouchButton bit={BUTTON_BITS.START} maskRef={maskRef} label="Start" className="gamepad-center-btn side-mid" />
        {/* Position-based mapping, matching keyboard.ts exactly: top=X, right=A, bottom=B, left=Y */}
        <DirectionalCluster
          maskRef={maskRef}
          ariaLabel="Face buttons"
          className="side-bottom gamepad-faces"
          bits={{ up: BUTTON_BITS.X, down: BUTTON_BITS.B, left: BUTTON_BITS.Y, right: BUTTON_BITS.A }}
          labels={{ up: 'X', down: 'B', left: 'Y', right: 'A' }}
        />
      </div>
    </div>
  );
}
