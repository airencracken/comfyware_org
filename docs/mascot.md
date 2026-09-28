# Comfyware mascot

A comfortable little robot in a sage-green sweater, curled into a cream armchair
with a terracotta mug of coffee. The chosen version uses clean shapes, restrained
shading, open oval eyes, and a small smile.

- Current asset: `site/assets/comfy-robot.png` (1254 × 1254, transparent RGBA PNG).
- Edited with the built-in `image_gen` tool on 2026-09-28.
- Edit target: `design/mascot-options/robot.png`, the selected robot concept.
- The original concept took inspiration from the simple face and outline of
  Imvault's keeper and the green/cream colors and gentle shading of Witmoot's
  Moot Knight. Its original prompt is in the
  [concept notes](../design/mascot-options/README.md).
- This edit reduces texture and mechanical details and changes the expression
  to address the requested simpler, less smug look.
- The generated PNG is copied unchanged, preserving its alpha channel. No CLI
  fallback or image post-processing was used.
- Used in the homepage introduction and homepage sharing metadata. Superseded
  concepts are kept outside the public site under `design/mascot-options/`.

## Final edit prompt

```text
Use case: style-transfer
Asset type: refinement of the selected Comfyware robot mascot for a small software website.
Input image: the attached robot.png is the EDIT TARGET. Preserve this robot's identity and the cozy concept: cream rounded screen head, little antenna, green sweater, coffee mug, curled-up feet, cream armchair, sage/cream/terracotta palette, full-body isolated composition and transparent background.
Primary request: make this robot a bit less visually complex and less smug-looking.
Expression change: replace the large upturned closed-eye arches, cheek/blush marks and jaunty smile with two small, simple OPEN oval eyes and a very small shallow, centered smile. No eyebrows or blush strokes. Keep the face modest, calm, friendly and gently attentive. The head should be nearly upright with just a slight relaxed lean, not cocked playfully. No smirk, broad grin or raised eyebrows. It should feel quietly comfortable and approachable.
Simplification: remove the stippled and knitted surface texture; use a plain soft sage sweater with just a few broad folds and minimal ribbing at the collar/cuffs. Reduce the number of seams, finger segments and nested mechanical rings. Simplify the feet into two rounded robot slippers with one simple sole shape each. Simplify the chair into large soft cushions with only essential contour lines. Use clean, mostly flat color fills with one restrained shadow tone per material and very few highlights. Keep clear dark outlines. Keep enough softness and gentle shading to belong with the original friendly Imvault and Witmoot mascot illustrations, but closer to the visual simplicity of Imvault's little keeper.
Preserve: the cozy armchair, both hands holding one terracotta mug of coffee, small steam curl, warm green-and-cream palette, recognizable robot anatomy, transparent negative space, full chair and feet inside the canvas.
Composition: one complete mascot, centered square canvas with comfortable transparent margins, readable at 250–350px display width.
Constraints: no text, watermark, extra props, new characters, background scene, opaque background or baked-in checkerboard. Do not turn it into an animal, human or a different mascot. Output one revised image with genuine alpha transparency.
```
