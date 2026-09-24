import { useEffect, useRef } from 'react';
import { usePikoSim } from './usePikoSim';
import { GamepadControls } from './GamepadControls';
import { setCustomBank, useCustomBank } from './simBank';
import { enterFullscreen, exitFullscreen, fullscreenSupported } from './fullscreen';

const LCD_SIZE = 240;

export function PlayTab({ onExit }: { onExit: () => void }) {
  const touchMaskRef = useRef(0);
  const customBank = useCustomBank();
  const { canvasRef, status, error, start } = usePikoSim(touchMaskRef);
  // Once the user taps Play the tab takes over the whole viewport (see .is-playing in
  // styles.css); errors stay in the normal page flow so the tab switcher is still reachable.
  const isPlaying = !error && status !== 'idle';

  // Both calls must run synchronously inside the click: start() creates the AudioContext and
  // enterFullscreen() calls requestFullscreen(), and each needs the user gesture to be active.
  const handlePlay = () => {
    start();
    void enterFullscreen();
  };
  const handleExit = () => {
    exitFullscreen();
    onExit();
  };
  // Leaving the tab by any other route must not strand the browser in fullscreen.
  useEffect(() => () => exitFullscreen(), []);

  return (
    <div className={isPlaying ? 'play-tab is-playing' : 'play-tab'}>
      {isPlaying ? (
        <button type="button" className="play-exit" onClick={handleExit} aria-label="Exit" title="Exit">
          ✕
        </button>
      ) : null}
      <div className="play-rotate-hint">
        <span>Rotate your phone to play</span>
      </div>
      <div className="play-content">
        {error ? (
          <div className="sim-demo-error play-error">Simulator failed to load: {error}</div>
        ) : status === 'idle' ? (
          <div className="play-start-screen">
            <h2>pikocore — play in your browser</h2>
            <p>Try the device right here, no install needed.</p>
            {customBank ? (
              <p className="play-bank">
                Your bank: {customBank.sampleCount} sample{customBank.sampleCount === 1 ? '' : 's'}{' '}
                <button type="button" className="text-button" onClick={() => setCustomBank(null)}>
                  Use demo bank
                </button>
              </p>
            ) : (
              <p className="play-bank">Demo bank. Add samples in the Loader tab and choose "Try in simulator".</p>
            )}
            <button type="button" className="primary play-button" onClick={handlePlay}>
              Play
            </button>
            {!fullscreenSupported() ? (
              <p className="play-hint">On iPhone, tap Share → Add to Home Screen to play in full screen.</p>
            ) : null}
          </div>
        ) : status === 'loading' ? (
          <div className="play-start-screen">
            <span className="spinner" aria-hidden="true" />
            <p>Loading simulator...</p>
          </div>
        ) : (
          <GamepadControls maskRef={touchMaskRef}>
            <canvas ref={canvasRef} width={LCD_SIZE} height={LCD_SIZE} className="sim-demo-canvas" />
          </GamepadControls>
        )}
      </div>
    </div>
  );
}
