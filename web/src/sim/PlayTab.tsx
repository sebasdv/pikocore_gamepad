import { useRef } from 'react';
import { usePikoSim } from './usePikoSim';
import { GamepadControls } from './GamepadControls';

const LCD_SIZE = 240;

export function PlayTab() {
  const touchMaskRef = useRef(0);
  const { canvasRef, status, error, start } = usePikoSim(touchMaskRef);

  return (
    <div className="play-tab">
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
            <button type="button" className="primary play-button" onClick={start}>
              Play
            </button>
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
