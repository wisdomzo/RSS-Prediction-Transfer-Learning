const test = require('node:test');
const assert = require('node:assert/strict');
const { createMotionClock, terrainHeight } = require('../web/download/scene-math.js');

test('paused or inactive scenes freeze elapsed time and resume without a jump', () => {
  const clock = createMotionClock();
  clock.tick(0); clock.tick(50);
  assert.equal(clock.elapsed, 0.05);
  clock.setPaused(true); clock.tick(2000);
  assert.equal(clock.elapsed, 0.05);
  clock.setPaused(false); clock.tick(5000);
  assert.equal(clock.elapsed, 0.05);
  clock.tick(5050);
  assert.equal(clock.elapsed, 0.1);
  clock.setActive(false); clock.tick(9000);
  clock.setActive(true); clock.tick(15000);
  assert.equal(clock.elapsed, 0.1);
  clock.tick(15050);
  assert.ok(Math.abs(clock.elapsed - 0.15) < 1e-9);
});

test('a slow frame cannot launch wavefronts far forward', () => {
  const clock = createMotionClock();
  clock.tick(0); clock.tick(10000);
  assert.ok(clock.elapsed <= 0.06);
});

test('terrain meets the base at every edge without negative heights', () => {
  for (let n = -5; n <= 5; n += 0.25) {
    assert.ok(Math.abs(terrainHeight(5, n)) < 1e-9);
    assert.ok(Math.abs(terrainHeight(n, -5)) < 1e-9);
    for (let z = -5; z <= 5; z += 0.25) assert.ok(terrainHeight(n, z) >= 0);
  }
  assert.ok(terrainHeight(-1.5, -1.2) > 1);
});
