import { useRef } from 'react';
import { clusterDirections, type ClusterDirections } from './cluster';

export interface ClusterBits {
  up: number;
  down: number;
  left: number;
  right: number;
}

interface DirectionalClusterProps {
  maskRef: { current: number };
  bits: ClusterBits;
  // Optional text drawn inside each arm (face buttons); the D-pad leaves it out — its shape
  // already says which way it points.
  labels?: Partial<Record<keyof ClusterBits, string>>;
  ariaLabel: string;
  className?: string;
}

const KEYS: Array<keyof ClusterBits> = ['up', 'down', 'left', 'right'];

// One touch surface for a whole 3x3 cross instead of four independent buttons: the pointer's
// position picks the pressed arms, so a corner presses two at once (diagonals — the firmware's
// clock-lock combo needs Down+Left) and a thumb can roll from one arm to the next. Each pointer
// is tracked separately so a second finger on the same cluster just adds to the mask.
export function DirectionalCluster({ maskRef, bits, labels, ariaLabel, className }: DirectionalClusterProps) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const pointersRef = useRef<Map<number, ClusterDirections>>(new Map());
  const clusterBits = bits.up | bits.down | bits.left | bits.right;

  const apply = () => {
    const active: ClusterDirections = { up: false, down: false, left: false, right: false };
    for (const dirs of pointersRef.current.values()) {
      for (const key of KEYS) if (dirs[key]) active[key] = true;
    }
    let next = 0;
    for (const key of KEYS) if (active[key]) next |= bits[key];
    maskRef.current = (maskRef.current & ~clusterBits) | next;
    // Highlight via data attributes (no React state: this runs on every pointer move).
    const root = rootRef.current;
    if (root) for (const key of KEYS) root.dataset[key] = active[key] ? 'true' : 'false';
  };

  const track = (event: React.PointerEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const half = Math.min(rect.width, rect.height) / 2;
    const dx = (event.clientX - (rect.left + rect.width / 2)) / half;
    const dy = (event.clientY - (rect.top + rect.height / 2)) / half;
    pointersRef.current.set(event.pointerId, clusterDirections(dx, dy));
    apply();
  };
  const release = (event: React.PointerEvent<HTMLDivElement>) => {
    pointersRef.current.delete(event.pointerId);
    apply();
  };

  return (
    <div
      ref={rootRef}
      className={`gamepad-cluster ${className ?? ''}`}
      role="group"
      aria-label={ariaLabel}
      onPointerDown={(event) => {
        event.preventDefault();
        event.currentTarget.setPointerCapture(event.pointerId);
        track(event);
      }}
      onPointerMove={(event) => {
        if (pointersRef.current.has(event.pointerId)) track(event);
      }}
      onPointerUp={release}
      onPointerCancel={release}
      onContextMenu={(event) => event.preventDefault()}
    >
      {KEYS.map((key) => (
        <span key={key} className={`cluster-arm cluster-arm-${key}`}>
          {labels?.[key]}
        </span>
      ))}
    </div>
  );
}
