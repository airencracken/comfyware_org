# Comfyware mascot

A comfortable little robot in a plain sage-green sweater, curled into a cream
armchair with a terracotta mug of coffee. The chosen version has a smooth head
without an antenna, simple feet and joints, open oval eyes, and a small smile.

- Current asset: `site/assets/comfy-robot.png` (1254 × 1254, transparent RGBA PNG).
- Edited with the built-in `image_gen` tool on 2026-09-28.
- Edit target: `site/assets/comfy-robot.png` at commit
  `ef931f9c27acf8bcd50a2d1851c1365e3e4a8f86`. The prior version and edit prompt
  remain in Git history.
- The original concept took inspiration from the simple face and outline of
  Imvault's keeper and the green/cream colors and gentle shading of Witmoot's
  Moot Knight. Its original prompt is in the
  [concept notes](../design/mascot-options/README.md).
- This pass removes the antenna and reduces sweater ribbing, mechanical joints,
  and small shading details while retaining the selected expression and pose.
- The generated PNG is copied unchanged, preserving its alpha channel. No CLI
  fallback or image post-processing was used.
- Used in the homepage introduction and homepage sharing metadata. Earlier
  concepts are kept outside the public site under `design/mascot-options/`.

## Final edit prompt

```text
Use case: precise-object-edit
Asset type: one more simplification pass on the existing Comfyware robot mascot.
Input image: the attached comfy-robot.png is the EDIT TARGET. This is the chosen character; preserve its identity, open oval eyes, tiny centered smile, cozy seated pose, coffee cup, sweater, cream armchair, palette and transparent background.
Primary request: make it a bit simpler. In particular, remove the antenna entirely.
Required changes:
1. Remove the complete antenna, including the green ball, stalk, and mounting base. The top of the robot's head must be a clean, uninterrupted rounded cream contour, with transparent space above it. No replacement tuft, button, wire, knob, hat, or other head ornament.
2. Simplify the remaining small details: make each side of the head one plain rounded ear/joint disc with minimal outlining; remove the circular ankle hardware and extra joint rings, leaving two smooth rounded robot feet with simple green soles. Keep hands clear and simple as they hold the mug.
3. Simplify the sweater to a plain sage garment with just the collar, cuff outlines, and a few broad folds. Remove most fine ribbing and unnecessary internal lines. Keep soft rounded sleeves and the cozy feeling.
4. Reduce small highlights and secondary shading shapes on the chair and robot. Use large clean cream/sage/terracotta color areas, restrained gentle shading, and confident dark outlines. Retain enough depth to match the same illustration rather than turning it into a flat pictogram.
Keep unchanged: the calm open-eyed expression and small smile, no eyebrows or blush; the overall proportions, comfortably curled-up posture, both hands cradling one terracotta coffee mug, soft cream armchair, warm friendly mood and full character visible. Keep the steam simple.
Composition: same single isolated mascot, centered square canvas with comfortable transparent margins. Make the visual details readable when displayed at 250 pixels wide.
Background: genuine alpha transparency, no colored background, ground plane, checkerboard, text, watermark, extra objects or characters. Return one revised mascot image.
```
