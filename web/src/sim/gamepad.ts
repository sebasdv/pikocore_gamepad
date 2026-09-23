import type { PikoSim } from './simModule';

// XINPUT_GAMEPAD_* bit values from sim/core/buttons.cpp's kXMap — piko_map_xinput() expects a
// mask built from these, not from sim::Button bits.
const X_DPAD_UP = 0x0001;
const X_DPAD_DOWN = 0x0002;
const X_DPAD_LEFT = 0x0004;
const X_DPAD_RIGHT = 0x0008;
const X_START = 0x0010;
const X_BACK = 0x0020;
const X_LEFT_SHOULDER = 0x0100;
const X_RIGHT_SHOULDER = 0x0200;
const X_A = 0x1000;
const X_B = 0x2000;
const X_X = 0x4000;
const X_Y = 0x8000;

// Standard Gamepad API button indices (https://www.w3.org/TR/gamepad/#remapping) line up with
// an Xbox-style pad's physical layout, same as XInput's wButtons.
const GAMEPAD_INDEX_TO_XINPUT: Array<[number, number]> = [
  [0, X_A],
  [1, X_B],
  [2, X_X],
  [3, X_Y],
  [4, X_LEFT_SHOULDER],
  [5, X_RIGHT_SHOULDER],
  [8, X_BACK],
  [9, X_START],
  [12, X_DPAD_UP],
  [13, X_DPAD_DOWN],
  [14, X_DPAD_LEFT],
  [15, X_DPAD_RIGHT],
];

export function pollGamepadMask(pad: Gamepad, piko: PikoSim): number {
  let xinputMask = 0;
  for (const [index, bit] of GAMEPAD_INDEX_TO_XINPUT) {
    const button = pad.buttons[index];
    if (button && button.pressed) xinputMask |= bit;
  }
  return piko.mapXinput(xinputMask);
}
