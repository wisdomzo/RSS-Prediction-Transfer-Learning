# Three.js r164

Vendored from the existing local `3dgs-demo/engine/three` copy (r164). MIT licensed.

`three.module.js` and `OrbitControls.js` are the upstream source. `three.local.js`
wraps the module body in an IIFE and exposes its named exports as
`window.ASSETThree`. `OrbitControls.local.js` replaces the bare `three` import
with this namespace and exposes `window.ASSETOrbitControls`.

Only module linkage is changed. The classic-script builds let `download.html`
work both over HTTP and directly from disk, without an import map or CDN.
