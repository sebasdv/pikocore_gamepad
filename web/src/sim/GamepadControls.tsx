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
  return (
    <div className="play-gamepad">
      <div className="play-gamepad-side play-gamepad-left">
        <TouchButton bit={BUTTON_BITS.L} maskRef={maskRef} label="L" className="gamepad-shoulder-btn" />
        <div className="play-gamepad-dpad">
          <TouchButton bit={BUTTON_BITS.UP} maskRef={maskRef} label="↑" className="gamepad-dpad-up" />
          <TouchButton bit={BUTTON_BITS.LEFT} maskRef={maskRef} label="←" className="gamepad-dpad-left" />
          <TouchButton bit={BUTTON_BITS.RIGHT} maskRef={maskRef} label="→" className="gamepad-dpad-right" />
          <TouchButton bit={BUTTON_BITS.DOWN} maskRef={maskRef} label="↓" className="gamepad-dpad-down" />
        </div>
      </div>
      <div className="play-gamepad-screen">{children}</div>
      <div className="play-gamepad-center">
        <TouchButton bit={BUTTON_BITS.SELECT} maskRef={maskRef} label="Select" className="gamepad-center-btn" />
        <TouchButton bit={BUTTON_BITS.START} maskRef={maskRef} label="Start" className="gamepad-center-btn" />
      </div>
      <div className="play-gamepad-side play-gamepad-right">
        <TouchButton bit={BUTTON_BITS.R} maskRef={maskRef} label="R" className="gamepad-shoulder-btn" />
        <div className="play-gamepad-faces">
          {/* Position-based mapping, matching keyboard.ts exactly: top=X, right=A, bottom=B, left=Y */}
          <TouchButton bit={BUTTON_BITS.X} maskRef={maskRef} label="X" className="gamepad-face-top" />
          <TouchButton bit={BUTTON_BITS.Y} maskRef={maskRef} label="Y" className="gamepad-face-left" />
          <TouchButton bit={BUTTON_BITS.A} maskRef={maskRef} label="A" className="gamepad-face-right" />
          <TouchButton bit={BUTTON_BITS.B} maskRef={maskRef} label="B" className="gamepad-face-bottom" />
        </div>
      </div>
    </div>
  );
}
