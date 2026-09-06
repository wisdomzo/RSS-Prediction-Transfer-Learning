# Download page design QA

Final result: passed local browser and automated checks, 2026-09-06.

## Approved direction

Silver/cobalt presentation with Japanese and English together. All three installer rows intentionally remain Coming soon. The final user request supersedes the monochrome terrain reference: the interactive landscape now includes green trees, naturally colored mountains, roads, buildings, rocks and three wireless base stations. Animated wavefronts illustrate a wireless environment; they are not propagation calculations.

## Evidence

- `design-preview/download-qa/natural-desktop-matched.png`: desktop, 1176 × 1024.
- `design-preview/download-qa/natural-mobile-matched.png`: mobile, 390 × 1024.
- `design-preview/download-qa/final-desktop-comparison.jpg`: reference and implementation comparison.
- `design-preview/download-qa/final-mobile-comparison.jpg`: reference 360 px and implementation 390 px, without rescaling.
- `design-preview/download-qa/natural-pause-a.png` and `natural-pause-b.png`: identical paused frames.
- `design-preview/download-qa/natural-rotated.png` and `natural-reset.png`: changed orbit and restored camera.

## Verification

- Three motion-clock/terrain tests passed; all local application and bundled classic scripts passed syntax checking.
- 32 local asset references and seven anchor targets resolve. The guide PDF matches the existing project PDF.
- Viewport widths 320, 390, 768, 1176 and 1440 have no horizontal overflow.
- Mouse rotation, keyboard controls, pause/resume and reset exercised. Reset flushes orbit damping; screenshot difference after reset is negligible.
- Mobile navigation, anchor navigation and FAQ expansion exercised.
- Three Coming soon rows have no active installer links.
- Browser console has no errors or warnings in the final preview.
- Fallback image is hidden from assistive technology while the interactive canvas is active.

## Corrections completed

Completed missing scene/page scripts and local assets; corrected pale terrain and vegetation colors; aligned tower foundations with terrain; cleared damping when resetting the camera; updated resource query versions; added a natural-color fallback and removed its duplicate accessibility announcement. Trees and repeated scene objects use instancing to limit rendering cost.

No unresolved material issue found in the checked views. The landscape is stylized real-time geometry rather than a photorealistic render. The page preserves the selected palette while giving the scene the requested natural colors.

## Coverage limits

Verified using the local HTTP preview in the in-app browser. Responsive checks do not replace physical iPhone/Safari or Windows browser testing. Direct file navigation was unavailable under browser URL policy, so that mode remains unverified. No external deployment was performed.

## Subsequent requested revision — 2026-09-06

Supersedes the earlier release and wave descriptions above: only horizontal expanding rings remain; three animated quadcopters share the pause clock; Apple Silicon v2.7.7 now links to the provided DMG; the incorrect fine-tuning PDF entry is removed. Intel and Windows remain Coming soon. The DMG HEAD request returned HTTP 200 with application/x-apple-diskimage. Updated browser screenshot and accessibility tree confirm rings, drones, an active Apple Silicon link and no PDF entry. JavaScript syntax and all three motion/terrain tests pass. Public website deployment is not configured in this checkout; changes are in the local HTML and preview.
