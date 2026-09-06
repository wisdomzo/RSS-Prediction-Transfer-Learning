# ASSET download page implementation plan

**Goal:** Add `web/download.html` matching the approved cobalt/silver bilingual design, with a rotatable mountain landscape, three base stations and animated conceptual wavefronts.

**Architecture:** Standalone HTML with local CSS, classic JavaScript and a locally bundled Three.js r164/OrbitControls. Keep all page assets inside `web`; no changes to the Python application. Classic scripts also support opening the HTML directly. Use a static image when WebGL is unavailable.

**Approved reference:** `exec-2048056b-c6a9-4b8f-8436-d0bfed7eb237.png` in the current task's generated images. Japanese and English coexist. All three installers are Coming soon, explicitly confirmed by the user.

## Work

- [x] Create page sections: navigation, bilingual hero, 3D scene and controls, three release rows, feature workflow, usage guide and footer.
- [x] Test motion-clock behavior before implementing: pause/hidden states freeze elapsed simulation time; resume never jumps; frame delta is bounded.
- [x] Implement a continuous terrain height field, mesh/wire grid, glass-like plinth, cellular towers and spherical wave arcs. Orbit controls support mouse, touch and a keyboard alternative. Reset camera and pause animation separately.
- [x] Add local configuration for future installer URLs, with disabled Coming soon states by default. Link to a local copy of the existing fine-tuning PDF and label its scope accurately.
- [x] Add reduced motion, offscreen/hidden suspension, responsive rendering and a WebGL fallback. No remote resources required at runtime.
- [x] Run syntax/unit checks, view desktop and mobile layouts, exercise reset/pause/rotation/navigation/guide and compare against the approved visual.
- [x] Save QA evidence, document configuration, and leave a local preview open.

## Files

`web/download.html`, `web/download/style.css`, `web/download/page.js`, `web/download/scene.js`, `web/download/scene-math.js`, `web/download/releases.js`, `web/vendor/three/`, `web/assets/download/`, `tests/test_download_motion.cjs`.

## Validation

Use Node's built-in test runner for the real clock and terrain helper. Use the in-app browser for rendered checks. Verify assets resolve from the web root, no CDN calls, no dead installer links, and no changes to the production app entry.

## Final scene revision

Implemented the requested natural colors, instanced green trees, roads, buildings and rocks in `scene-environment.js`. These remain part of the rotatable Three.js scene. See `design-qa.md` for verification and browser coverage limits.
