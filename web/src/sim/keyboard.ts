// Mirrors sim/core/buttons.h's Button enum order exactly — a bit index here must match that
// enum's declaration order, since piko_set_buttons() interprets the mask with the same bits.
export const BUTTON_BITS = {
  UP: 1 << 0,
  DOWN: 1 << 1,
  LEFT: 1 << 2,
  RIGHT: 1 << 3,
  Y: 1 << 4,
  X: 1 << 5,
  B: 1 << 6,
  A: 1 << 7,
  SELECT: 1 << 8,
  START: 1 << 9,
  L: 1 << 10,
  R: 1 << 11,
} as const;

// Same mapping as sim/README.md's table (face buttons by position, not letter).
const KEY_MAP: Record<string, number> = {
  ArrowUp: BUTTON_BITS.UP,
  ArrowDown: BUTTON_BITS.DOWN,
  ArrowLeft: BUTTON_BITS.LEFT,
  ArrowRight: BUTTON_BITS.RIGHT,
  KeyW: BUTTON_BITS.X,
  KeyD: BUTTON_BITS.A,
  KeyS: BUTTON_BITS.B,
  KeyA: BUTTON_BITS.Y,
  KeyQ: BUTTON_BITS.L,
  KeyE: BUTTON_BITS.R,
  Backspace: BUTTON_BITS.SELECT,
  Enter: BUTTON_BITS.START,
};

export function keyToButtonBit(code: string): number | null {
  return KEY_MAP[code] ?? null;
}
