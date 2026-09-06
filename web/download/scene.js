/* ASSET's illustrative, interactive landscape. Geometry is conceptual, not RF simulation data. */
(function () {
  'use strict';
  const viewport = document.getElementById('scene-viewport');
  const canvas = document.getElementById('terrain-canvas');
  const resetButton = document.getElementById('reset-view');
  const pauseButton = document.getElementById('pause-motion');
  const status = document.getElementById('scene-status');
  function fallback(message) {
    viewport.classList.remove('is-ready');
    document.getElementById('scene-fallback').removeAttribute('aria-hidden');
    viewport.setAttribute('aria-busy', 'false');
    canvas.hidden = true;
    resetButton.disabled = pauseButton.disabled = true;
    status.textContent = message || '静止画プレビュー / Static preview — 3D unavailable';
    document.getElementById('scene-help').lastElementChild.textContent = '静止画 / Static view';
  }
  if (!window.ASSETThree || !window.ASSETOrbitControls || !window.ASSETSceneMath) { fallback(); return; }
  const T = window.ASSETThree;
  const { terrainHeight, createMotionClock } = window.ASSETSceneMath;
  let renderer;
  try {
    renderer = new T.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'low-power' });
  } catch (_) { fallback(); return; }
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const mobile = window.matchMedia('(max-width: 760px)');
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, mobile.matches ? 1.5 : 2));
  renderer.setClearColor(0xf5f7fc, 0);
  renderer.outputColorSpace = T.SRGBColorSpace;
  renderer.toneMapping = T.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.9;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = T.PCFSoftShadowMap;
  const scene = new T.Scene();
  const camera = new T.PerspectiveCamera(32, 1, 0.1, 80);
  const home = new T.Vector3(11.3, 9.6, 13.6);
  camera.position.copy(home);
  const controls = new window.ASSETOrbitControls(camera, canvas);
  controls.target.set(0, 1.0, 0);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.enablePan = false;
  controls.enableZoom = false;
  controls.minPolarAngle = 0.25;
  controls.maxPolarAngle = Math.PI / 2.2;
  controls.rotateSpeed = 0.65;
  controls.update();
  controls.saveState();

  scene.add(new T.HemisphereLight(0xf8fbff, 0xa9b7d0, 0.85));
  const sun = new T.DirectionalLight(0xffffff, 1.9);
  sun.position.set(-5, 12, 6);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024);
  Object.assign(sun.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8, near: 0.5, far: 35 });
  sun.shadow.bias = -0.001;
  sun.shadow.normalBias = 0.03;
  scene.add(sun);
  const rim = new T.DirectionalLight(0xadcaff, 0.9);
  rim.position.set(6, 6, -8); scene.add(rim);

  // A small studio environment gives the glass base genuine reflections.
  const studio = new T.Scene();
  studio.background = new T.Color(0xeaf0fb);
  const panelMaterial = new T.MeshBasicMaterial({ color: 0xffffff, side: T.DoubleSide });
  for (const [x, y, z, rx, ry] of [[0, 8, 0, Math.PI / 2, 0], [-8, 3, 0, 0, Math.PI / 2], [0, 2, -8, 0, 0]]) {
    const panel = new T.Mesh(new T.PlaneGeometry(14, 8), panelMaterial);
    panel.position.set(x, y, z); panel.rotation.set(rx, ry, 0); studio.add(panel);
  }
  const pmrem = new T.PMREMGenerator(renderer);
  const environment = pmrem.fromScene(studio, 0.01, 0.1, 30);
  scene.environment = environment.texture;
  pmrem.dispose();
  studio.children.forEach((panel) => panel.geometry.dispose());
  panelMaterial.dispose();

  const world = new T.Group(); scene.add(world);
  const ground = new T.Mesh(new T.PlaneGeometry(25, 25), new T.ShadowMaterial({ color: 0x617697, opacity: 0.12 }));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -0.43; ground.receiveShadow = true; scene.add(ground);

  const outline = new T.Shape();
  const half = 5.1, bevel = 0.1;
  outline.moveTo(-half + bevel, -half);
  outline.lineTo(half - bevel, -half); outline.quadraticCurveTo(half, -half, half, -half + bevel);
  outline.lineTo(half, half - bevel); outline.quadraticCurveTo(half, half, half - bevel, half);
  outline.lineTo(-half + bevel, half); outline.quadraticCurveTo(-half, half, -half, half - bevel);
  outline.lineTo(-half, -half + bevel); outline.quadraticCurveTo(-half, -half, -half + bevel, -half);
  const glassGeometry = new T.ExtrudeGeometry(outline, {depth: 0.29, bevelEnabled: true, bevelSegments: 3, steps: 1, bevelSize: 0.035, bevelThickness: 0.035});
  glassGeometry.rotateX(-Math.PI / 2);
  glassGeometry.translate(0, -0.16, 0);
  const base = new T.Mesh(glassGeometry, new T.MeshPhysicalMaterial({
    color: 0xdce9fc, metalness: 0.05, roughness: 0.12, transmission: 0.78,
    thickness: 0.5, ior: 1.46, transparent: true, opacity: 0.82, clearcoat: 1
  }));
  base.position.y = -0.2; base.castShadow = true; world.add(base);
  const baseEdges = new T.LineSegments(new T.EdgesGeometry(base.geometry), new T.LineBasicMaterial({ color: 0x718caa, transparent: true, opacity: 0.4 }));
  baseEdges.position.copy(base.position); world.add(baseEdges);
  const lower = new T.Mesh(new T.BoxGeometry(9.99, 0.025, 9.99), new T.MeshPhysicalMaterial({ color: 0xe4eafa, metalness: 0.35, roughness: 0.3, transparent: true, opacity: 0.32 }));
  lower.position.y = -0.34; world.add(lower);

  const resolution = mobile.matches ? 100 : 150;
  const terrainGeometry = new T.PlaneGeometry(10, 10, resolution, resolution);
  terrainGeometry.rotateX(-Math.PI / 2);
  const positions = terrainGeometry.attributes.position;
  const colors = [];
  const grass = new T.Color(0x6d954f), forest = new T.Color(0x476d3c), rock = new T.Color(0x94836b), summit = new T.Color(0xb5b3a4);
  for (let i = 0; i < positions.count; i++) {
    const x=positions.getX(i), z=positions.getZ(i), h=terrainHeight(x,z);
    positions.setY(i,h+0.018);
    const slope=Math.hypot(terrainHeight(x+.06,z)-h,terrainHeight(x,z+.06)-h)/.06;
    const color=grass.clone().lerp(forest,Math.min(1,h*.65));
    color.lerp(rock,Math.max(0,Math.min(.9,(h-1.05)*.48+(slope-1.2)*.22)));
    if(h>2.1)color.lerp(summit,Math.min(.72,(h-2.1)*.55));
    color.multiplyScalar(.94+.06*Math.sin(x*4.3+Math.cos(z*3)));
    colors.push(color.r,color.g,color.b);
  }
  terrainGeometry.setAttribute('color',new T.Float32BufferAttribute(colors,3));
  terrainGeometry.computeVertexNormals();
  const terrain = new T.Mesh(terrainGeometry, new T.MeshStandardMaterial({ color: 0xffffff, vertexColors:true, roughness: 0.95, metalness: 0, envMapIntensity: 0.25 }));
  terrain.receiveShadow = true; terrain.castShadow = true; world.add(terrain);

  // Orthogonal survey mesh preserves the fine-line topography of the approved design.
  const gridPoints = [];
  const grid = mobile.matches ? 65 : 92;
  for (let i = 0; i <= grid; i++) {
    const fixed = -5 + i * 10 / grid;
    for (let j = 0; j < grid; j++) {
      const a = -5 + j * 10 / grid, b = -5 + (j + 1) * 10 / grid;
      gridPoints.push(fixed, terrainHeight(fixed, a) + 0.026, a, fixed, terrainHeight(fixed, b) + 0.026, b);
      gridPoints.push(a, terrainHeight(a, fixed) + 0.026, fixed, b, terrainHeight(b, fixed) + 0.026, fixed);
    }
  }
  const gridGeometry = new T.BufferGeometry();
  gridGeometry.setAttribute('position', new T.Float32BufferAttribute(gridPoints, 3));
  world.add(new T.LineSegments(gridGeometry, new T.LineBasicMaterial({ color: 0x34545d, transparent: true, opacity: 0.025, depthWrite: false })));
  if (window.ASSETNaturalEnvironment) window.ASSETNaturalEnvironment(T, world, terrainHeight, mobile.matches);

  const steel = new T.MeshStandardMaterial({ color: 0x415979, metalness: 0.72, roughness: 0.24 });
  const white = new T.MeshStandardMaterial({ color: 0xbdcce1, metalness: 0.35, roughness: 0.3 });
  const blue = new T.MeshStandardMaterial({ color: 0x2454ed, emissive: 0x174aff, emissiveIntensity: 0.22, metalness: 0.3, roughness: 0.3 });
  function bar(group, a, b, radius = 0.015, material = steel) {
    const from = new T.Vector3(...a), to = new T.Vector3(...b), vector = to.clone().sub(from);
    const mesh = new T.Mesh(new T.CylinderGeometry(radius, radius, vector.length(), 5), material);
    mesh.position.copy(from.add(to).multiplyScalar(0.5));
    mesh.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), vector.normalize());
    mesh.castShadow = true; group.add(mesh);
  }
  function station(x, z, height, lattice) {
    const group = new T.Group();
    group.position.set(x, terrainHeight(x, z) + 0.02, z);
    world.add(group);
    const pad = new T.Mesh(new T.BoxGeometry(0.52, 0.08, 0.52), white);
    pad.position.y = 0.04; pad.receiveShadow = true; group.add(pad);
    if (lattice) {
      const corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
      for (let level = 0; level < 5; level++) {
        const y0 = 0.08 + level * height / 5, y1 = 0.08 + (level + 1) * height / 5;
        const r0 = 0.19 * (1 - level / 7), r1 = 0.19 * (1 - (level + 1) / 7);
        corners.forEach(([cx, cz], index) => {
          const [nx, nz] = corners[(index + 1) % 4];
          bar(group, [cx * r0, y0, cz * r0], [cx * r1, y1, cz * r1]);
          bar(group, [cx * r0, y0, cz * r0], [nx * r1, y1, nz * r1], 0.008);
          bar(group, [cx * r1, y1, cz * r1], [nx * r0, y0, nz * r0], 0.008);
        });
      }
    } else {
      bar(group, [0, 0.06, 0], [0, height + 0.14, 0], 0.032);
      const cabinet = new T.Mesh(new T.BoxGeometry(0.29, 0.3, 0.24), white);
      cabinet.position.set(0.15, 0.23, 0.1); cabinet.castShadow = true; group.add(cabinet);
    }
    for (let n = 0; n < 3; n++) {
      const angle = n * Math.PI * 2 / 3;
      const px = Math.sin(angle) * 0.13, pz = Math.cos(angle) * 0.13;
      bar(group, [0, height - 0.12, 0], [px, height - 0.12, pz], 0.014);
      const antenna = new T.Mesh(new T.BoxGeometry(0.105, 0.42, 0.075), white);
      antenna.position.set(px, height - 0.08, pz); antenna.rotation.y = angle; antenna.castShadow = true; group.add(antenna);
    }
    bar(group, [0, height, 0], [0, height + 0.34, 0], 0.012);
    const tip = new T.Mesh(new T.SphereGeometry(0.027, 8, 8), blue);
    tip.position.y = height + 0.34; group.add(tip);
    return new T.Vector3(x, group.position.y + height + 0.1, z);
  }
  const sources = [station(-3.4, 2.2, 1.42, true), station(1.35, -1.8, 1.1, false), station(3.15, 2.35, 0.98, false)];
  const waves = [];
  const ringPoints = Array.from({ length: 81 }, (_, n) => {
    const angle = n / 80 * Math.PI * 2;
    return new T.Vector3(Math.cos(angle), 0, Math.sin(angle));
  });
  const horizontalArc = new T.BufferGeometry().setFromPoints(ringPoints);
  sources.forEach((source, sourceIndex) => {
    for (let n = 0; n < 3; n++) {
      const wave = new T.Group(); wave.position.copy(source); world.add(wave);
      const material = new T.LineBasicMaterial({ color: 0x356cff, toneMapped: false, transparent: true, opacity: 0.32, depthWrite: false });
      wave.add(new T.Line(horizontalArc, material));
      waves.push({ group: wave, material, offset: n / 3 + sourceIndex * 0.13 });
    }
  });

  // Small quadcopters share the scene clock so pause and reduced motion apply.
  const drones = [];
  const droneShell = new T.MeshStandardMaterial({ color: 0xf0f3f6, metalness: 0.35, roughness: 0.4 });
  const droneDark = new T.MeshStandardMaterial({ color: 0x253345, roughness: 0.6 });
  for (let i = 0; i < 3; i++) {
    const drone = new T.Group(), rotors = [];
    const body = new T.Mesh(new T.BoxGeometry(0.23, 0.09, 0.16), droneShell);
    drone.add(body);
    const cameraPod = new T.Mesh(new T.SphereGeometry(0.045, 10, 8), droneDark);
    cameraPod.position.set(0, -0.065, 0.07); drone.add(cameraPod);
    for (const x of [-0.18, 0.18]) for (const z of [-0.18, 0.18]) {
      const arm = new T.Mesh(new T.BoxGeometry(0.27, 0.025, 0.035), droneShell);
      arm.position.set(x / 2, 0, z / 2); arm.rotation.y = -Math.atan2(z, x); drone.add(arm);
      const motor = new T.Mesh(new T.CylinderGeometry(0.028, 0.028, 0.06, 8), droneDark);
      motor.position.set(x, 0.02, z); drone.add(motor);
      const rotor = new T.Mesh(new T.BoxGeometry(0.25, 0.008, 0.024), droneDark);
      rotor.position.set(x, 0.057, z); drone.add(rotor); rotors.push(rotor);
    }
    world.add(drone); drones.push({ drone, rotors, phase: i * Math.PI * 2 / 3 });
  }

  const clock = createMotionClock(); clock.setPaused(reduced.matches);
  let request = 0, inView = true, disposed = false;
  function draw(now) {
    request = 0;
    if (disposed) return;
    const elapsed = clock.tick(now);
    waves.forEach(({ group, material, offset }) => {
      const phase = (elapsed * 0.22 + offset) % 1;
      group.scale.setScalar(0.12 + phase * 2.1);
      material.opacity = 0.5 * Math.sin(phase * Math.PI) * (1 - phase * 0.55);
    });
    drones.forEach(({ drone, rotors, phase }) => {
      const angle = elapsed * 0.12 + phase;
      drone.position.set(Math.cos(angle) * 3.3, 3.35 + Math.sin(angle * 2 + phase) * 0.18, Math.sin(angle) * 2.3);
      drone.rotation.set(Math.sin(angle) * 0.04, -angle, Math.cos(angle) * 0.06);
      rotors.forEach((rotor, i) => { rotor.rotation.y = elapsed * 35 * (i % 2 ? -1 : 1); });
    });
    controls.update();
    renderer.render(scene, camera);
    if (clock.active && !clock.paused) schedule();
  }
  function schedule() { if (!request && !disposed) request = requestAnimationFrame(draw); }
  function updateActivity() {
    clock.setActive(inView && !document.hidden);
    if (clock.active) schedule();
    else if (request) { cancelAnimationFrame(request); request = 0; }
  }
  function updateMotionButton() {
    pauseButton.setAttribute('aria-pressed', String(clock.paused));
    document.getElementById('motion-ja').textContent = clock.paused ? '再生' : '一時停止';
    document.getElementById('motion-en').textContent = clock.paused ? 'Play' : 'Pause';
    document.getElementById('motion-icon').src = 'assets/download/' + (clock.paused ? 'play' : 'pause') + '.svg';
  }
  pauseButton.addEventListener('click', () => { clock.setPaused(!clock.paused); updateMotionButton(); schedule(); });
  function resetView() {
    controls.enableDamping = false;
    controls.reset();
    camera.position.copy(home); controls.target.set(0, 1.0, 0); controls.update(); controls.enableDamping = true; schedule();
  }
  resetButton.addEventListener('click', resetView);
  controls.addEventListener('change', schedule);
  canvas.addEventListener('keydown', (event) => {
    if (event.key === 'Home') { event.preventDefault(); resetView(); return; }
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
    event.preventDefault();
    const offset = camera.position.clone().sub(controls.target), spherical = new T.Spherical().setFromVector3(offset);
    if (event.key === 'ArrowLeft') spherical.theta -= 0.12;
    if (event.key === 'ArrowRight') spherical.theta += 0.12;
    if (event.key === 'ArrowUp') spherical.phi = Math.max(controls.minPolarAngle, spherical.phi - 0.09);
    if (event.key === 'ArrowDown') spherical.phi = Math.min(controls.maxPolarAngle, spherical.phi + 0.09);
    camera.position.copy(controls.target).add(new T.Vector3().setFromSpherical(spherical));
    controls.update(); schedule();
  });
  const observer = new ResizeObserver(() => {
    const width = viewport.clientWidth, height = viewport.clientHeight;
    if (!width || !height) return;
    camera.aspect = width / height;
    camera.fov = camera.aspect < 1.2 ? 40 : 32;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false); schedule();
  });
  observer.observe(viewport);
  const intersection = new IntersectionObserver((entries) => { inView = entries[0].isIntersecting; updateActivity(); });
  intersection.observe(viewport);
  document.addEventListener('visibilitychange', updateActivity);
  reduced.addEventListener('change', () => { clock.setPaused(reduced.matches); updateMotionButton(); schedule(); });
  canvas.addEventListener('webglcontextlost', (event) => {
    event.preventDefault(); disposed = true; cancelAnimationFrame(request);
    fallback('3D 接続が中断されました / 3D interrupted — reload to retry');
  });
  window.addEventListener('pagehide', (event) => {
    if (event.persisted) return;
    disposed = true; cancelAnimationFrame(request); observer.disconnect(); intersection.disconnect();
    controls.dispose(); renderer.dispose(); environment.dispose();
  });
  resetButton.disabled = pauseButton.disabled = false;
  updateMotionButton();
  viewport.classList.add('is-ready'); viewport.setAttribute('aria-busy', 'false');
  document.getElementById('scene-fallback').setAttribute('aria-hidden', 'true');
  schedule();
})();
