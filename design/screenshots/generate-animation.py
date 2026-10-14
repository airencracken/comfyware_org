"""Generate a local demo GIF whose first frame has visible artwork.

Requires Pillow only when regenerating this sample fixture.
"""
from pathlib import Path
from PIL import Image, ImageDraw

frames = []
for frame in range(16):
    image = Image.new('RGB', (360, 240), (216, 229, 239))
    drawing = ImageDraw.Draw(image)
    left = round((frame + 4) % 16 / 16 * 432) - 72
    drawing.rectangle((left, 0, left + 71, 239), fill=[
        (110, 168, 254), (246, 173, 85), (242, 112, 122), (110, 231, 168),
    ][frame % 4])
    frames.append(image)
frames[0].save(Path(__file__).with_name('animation.gif'), save_all=True,
               append_images=frames[1:], duration=80, loop=0)
