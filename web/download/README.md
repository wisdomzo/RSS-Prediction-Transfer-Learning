# ASSET download / introduction page

Open `../download.html` with its sibling folders intact, or serve `web`:

```sh
python3 -m http.server 8796 --bind 127.0.0.1 --directory web
```

Then open `http://127.0.0.1:8796/download.html`.

## Release configuration

Apple Silicon v2.7.7 is available. Intel and Windows remain **準備中 / Coming soon**.
Edit `releases.js` to enable an installer:

```js
window.ASSET_RELEASES = {
  macArm: { url: 'installers/ASSET-mac-arm64.zip', version: 'v2.7.4' },
  macIntel: { url: null, version: null },
  windows: { url: null, version: null }
};
```

The path is relative to `download.html`. Absolute HTTPS URLs also work.
The example is illustrative: no installer is currently included. Empty or
invalid URLs keep the row in Coming soon state. Set the actual version when
publishing; don't infer it from the page code. Publish the entire `web` folder,
or at least `download.html`, `download`, `vendor/three`, and `assets/download`.

## Scene and accessibility

- Drag with mouse or one finger to orbit; dragging is confined to the canvas.
- Arrow keys rotate the focused canvas; Home and Reset view restore the camera.
- Pause stops wavefront animation without disabling manual camera rotation.
- Reduced motion starts paused. Leaving the viewport or hiding the tab suspends animation.
- No external CDN, remote font, analytics or backend request is used.
- A generated still image is the fallback if WebGL cannot initialize or is lost.
- The terrain and wavefronts are conceptual artwork, not calculated propagation results.

`style.css` owns the cobalt/silver palette and the 760px mobile breakpoint.
`scene.js` owns the Three.js renderer; `scene-math.js` owns terrain and clock math.
`scene-environment.js` adds the road, buildings and instanced forest. The natural
colors, vegetation and architecture reflect the user's final scene revision.
If updating these files on an existing deployment, also increment the query
version in `download.html` to prevent stale cached scripts.

The incorrect fine-tuning PDF entry has been removed. Standard icons come from Lucide under its included license.

## Verification

```sh
node --test tests/test_download_motion.cjs
```

Rendered QA evidence lives in `design-preview/download-qa/` and the project-root
`design-qa.md`. Responsive viewport checks are not physical iPhone testing.

The scene uses expanding horizontal rings and three animated quadcopters. Pause applies to both flight and wave animation.

`scene-life.js` adds four hikers, six town pedestrians, three cars following the road, and an illustrative satellite with signal rings. All use the shared animation clock. Zoom uses wheel, pinch, +/- buttons or keyboard +/-; orbit distance is bounded to 9–28 scene units. Reset restores the default overview. Satellite altitude and actor scales are illustrative.

Weather controls independently select Clear / Cloudy / Snow and Day / Night. `scene-weather.js` manages light levels, clouds, terrain snow tint, particle snow and emissive windows. Snow and clouds pause with the shared clock; mobile uses fewer snow particles. These are illustrative weather presets, not live forecasts.

Reset (and Home) restores the default camera plus Clear / Day, synchronizing both selectors. Three cloud banks drift independently in cloudy/snow weather; pause freezes their positions.
