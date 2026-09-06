/* Pure terrain and animation helpers shared by the scene and its tests. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ASSETSceneMath = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function rawHeight(x, z) {
    const edge = Math.max(0, 1 - Math.pow(Math.max(Math.abs(x), Math.abs(z)) / 5, 8));
    const peaks = [
      [-1.5, -1.2, 2.7, 1.5], [1.35, -1.8, 3.15, 1.35],
      [1.1, 1.25, 2.15, 1.35], [-2.1, 1.7, 1.25, 0.9], [3.1, 0.2, 0.9, 1.0], [-2.5, -3, 1.1, 1.1], [2.8, -2.5, 1.0, 1.0]
    ];
    let height = 0;
    for (const [px, pz, amplitude, width] of peaks) {
      const radius = Math.hypot(x - px, z - pz) / width;
      height += amplitude * Math.exp(-Math.pow(radius, 1.6) * 1.4);
    }
    const detail = 1 + 0.09 * Math.sin(x * 8 + Math.cos(z * 3)) * Math.cos(z * 7)
      + 0.03 * Math.sin(x * 19 + z * 11);
    return Math.max(0, height * detail * edge);
  }

  function terrainHeight(x, z) {
    const height = rawHeight(x, z);
    for (const [sx, sz] of [[-3.4, 2.2], [1.35, -1.8], [3.15, 2.35]]) {
      const distance = Math.hypot(x - sx, z - sz);
      if (distance < 0.5) {
        const blend = Math.max(0, Math.min(1, (distance - 0.34) / 0.16));
        const smooth = blend * blend * (3 - 2 * blend);
        return rawHeight(sx, sz) * (1 - smooth) + height * smooth;
      }
    }
    return height;
  }

  function createMotionClock() {
    let elapsed = 0, last = null, paused = false, active = true;
    return {
      get elapsed() { return elapsed; },
      get paused() { return paused; },
      get active() { return active; },
      setPaused(value) { paused = Boolean(value); last = null; },
      setActive(value) { active = Boolean(value); last = null; },
      tick(now) {
        if (last !== null && active && !paused) elapsed += Math.max(0, Math.min((now - last) / 1000, 0.05));
        last = now;
        return elapsed;
      }
    };
  }
  return { terrainHeight, createMotionClock };
});
