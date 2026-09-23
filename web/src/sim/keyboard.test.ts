import { describe, expect, it } from 'vitest';
import { BUTTON_BITS, keyToButtonBit } from './keyboard';

describe('keyToButtonBit', () => {
  it('maps arrow keys to D-pad bits', () => {
    expect(keyToButtonBit('ArrowUp')).toBe(BUTTON_BITS.UP);
    expect(keyToButtonBit('ArrowLeft')).toBe(BUTTON_BITS.LEFT);
  });

  it('maps face buttons by position, not letter (W is the top face button)', () => {
    expect(keyToButtonBit('KeyW')).toBe(BUTTON_BITS.X);
  });

  it('returns null for unmapped keys', () => {
    expect(keyToButtonBit('KeyZ')).toBeNull();
  });
});
