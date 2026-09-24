type LockableOrientation = ScreenOrientation & {
  lock?: (orientation: 'landscape') => Promise<void>;
};

export function fullscreenSupported(): boolean {
  return typeof document !== 'undefined' && typeof document.documentElement.requestFullscreen === 'function';
}

// Only take over the whole screen on touch-first devices; on a desktop the fixed overlay
// filling the window is enough and yanking the browser into fullscreen would be intrusive.
function isTouchFirst(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(pointer: coarse)').matches;
}

// Must be called synchronously from a user gesture (the Play button's click handler):
// requestFullscreen() runs before the first await, so the gesture is still active.
export async function enterFullscreen(): Promise<void> {
  if (!isTouchFirst()) return;
  try {
    if (!document.fullscreenElement && fullscreenSupported()) {
      await document.documentElement.requestFullscreen({ navigationUI: 'hide' });
    }
    // Android Chrome only honors lock() while fullscreen; iOS Safari has neither API.
    await (screen.orientation as LockableOrientation | undefined)?.lock?.('landscape');
  } catch {
    // Unsupported or denied: the fixed 100dvh overlay still fills the viewport.
  }
}

export function exitFullscreen(): void {
  try {
    screen.orientation?.unlock?.();
  } catch {
    // unlock() throws when nothing was locked; nothing to undo.
  }
  if (typeof document !== 'undefined' && document.fullscreenElement) {
    void document.exitFullscreen().catch(() => {});
  }
}
