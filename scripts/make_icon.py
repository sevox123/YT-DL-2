"""Generates assets/icon.png and assets/icon.ico (run: python scripts/make_icon.py)."""
import os
import numpy as np
from PIL import Image, ImageDraw

S = 1024
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
os.makedirs(OUT, exist_ok=True)

# diagonal gradient violet -> pink
c1, c2 = np.array([124, 92, 255]), np.array([255, 92, 147])
yy, xx = np.mgrid[0:S, 0:S]
t = ((xx + yy) / (2 * (S - 1)))[..., None]
grad = (c1 * (1 - t) + c2 * t).astype("uint8")
img = Image.fromarray(grad, "RGB").convert("RGBA")

mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), radius=230, fill=255)
img.putalpha(mask)

d = ImageDraw.Draw(img)
# rounded play triangle
tri = [(360, 270), (360, 750), (790, 510)]
d.polygon(tri, fill="white")
d.line(tri + [tri[0]], fill="white", width=70, joint="curve")
for p in tri:
    d.ellipse((p[0] - 35, p[1] - 35, p[0] + 35, p[1] + 35), fill="white")

# download badge
cx, cy, r = 735, 735, 205
d.ellipse((cx - r - 24, cy - r - 24, cx + r + 24, cy + r + 24), fill=(255, 255, 255, 255))
d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(18, 18, 26, 255))
w = 46
d.line((cx, cy - 110, cx, cy + 40), fill="white", width=w)
d.line((cx - 85, cy - 25, cx, cy + 70), fill="white", width=w)
d.line((cx + 85, cy - 25, cx, cy + 70), fill="white", width=w)
d.line((cx - 95, cy + 115, cx + 95, cy + 115), fill="white", width=w)
for x, y in ((cx, cy - 110), (cx - 85, cy - 25), (cx + 85, cy - 25), (cx - 95, cy + 115), (cx + 95, cy + 115)):
    d.ellipse((x - w // 2, y - w // 2, x + w // 2, y + w // 2), fill="white")

img.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "icon.png"))
img.save(os.path.join(OUT, "icon.ico"), sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("icon written to", OUT)
