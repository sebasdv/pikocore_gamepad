export interface ClusterDirections {
  up: boolean;
  down: boolean;
  left: boolean;
  right: boolean;
}

// The cluster is a 3x3 grid (arms on the edge cells, dead zone in the center, diagonals in the
// corners). A cell edge sits at 1/3 of the width, i.e. ~0.33 of the half-size; a slightly smaller
// threshold makes an off-center press still register.
const THRESHOLD = 0.3;

// dx/dy are the pointer's offset from the cluster center, normalized so ±1 is the cluster's edge.
// Values beyond ±1 (a thumb that slid outside while the pointer is captured) keep counting.
export function clusterDirections(dx: number, dy: number): ClusterDirections {
  return { up: dy < -THRESHOLD, down: dy > THRESHOLD, left: dx < -THRESHOLD, right: dx > THRESHOLD };
}
