import { useSyncExternalStore } from 'react';

export interface CustomBank {
  bytes: Uint8Array;
  sampleCount: number;
}

// The bank the simulator boots with instead of the bundled demo. Set from the loader tab
// ("Try in simulator") and read once when the simulator starts, so the loader's samples never
// have to be threaded through props.
let customBank: CustomBank | null = null;
const listeners = new Set<() => void>();

export function getCustomBank(): CustomBank | null {
  return customBank;
}

export function setCustomBank(bank: CustomBank | null): void {
  customBank = bank;
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useCustomBank(): CustomBank | null {
  return useSyncExternalStore(subscribe, getCustomBank);
}
