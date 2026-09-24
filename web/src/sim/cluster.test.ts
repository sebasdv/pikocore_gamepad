import { describe, expect, it } from 'vitest';
import { clusterDirections } from './cluster';

const none = { up: false, down: false, left: false, right: false };

describe('clusterDirections', () => {
  it('presses nothing in the dead zone around the center', () => {
    expect(clusterDirections(0, 0)).toEqual(none);
    expect(clusterDirections(0.2, -0.2)).toEqual(none);
  });

  it('presses one direction along an axis', () => {
    expect(clusterDirections(0, -0.8)).toEqual({ ...none, up: true });
    expect(clusterDirections(0, 0.8)).toEqual({ ...none, down: true });
    expect(clusterDirections(-0.8, 0)).toEqual({ ...none, left: true });
    expect(clusterDirections(0.8, 0.1)).toEqual({ ...none, right: true });
  });

  it('presses two directions in the corners (diagonals)', () => {
    expect(clusterDirections(-0.7, 0.7)).toEqual({ ...none, down: true, left: true });
    expect(clusterDirections(0.7, -0.7)).toEqual({ ...none, up: true, right: true });
  });

  it('keeps counting when the thumb slides past the cluster edge', () => {
    expect(clusterDirections(3, -0.1)).toEqual({ ...none, right: true });
    expect(clusterDirections(-2, 2)).toEqual({ ...none, down: true, left: true });
  });
});
