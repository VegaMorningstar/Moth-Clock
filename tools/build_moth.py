# Turns the photo cutout into a resolution-independent SVG.
#
# The moth is re-stitched from the photo: stitches are laid on a jittered grid over
# the cutout, each one taking its colour from the photo at that spot and its angle
# from the direction the thread runs there (structure tensor of the photo's light).
# The silhouette, veins and margins therefore stay where the photo has them, but
# every stitch is a crisp vector line. The disk is a clean satin fill clipped to
# the photo's disk shape, and the photo's light and shade rides on top as relief.
#
# Usage: python tools/build_moth.py source/moth-cutout.png moth.svg

import base64
import io
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure

src, dst = sys.argv[1], sys.argv[2]
img = np.asarray(Image.open(src).convert('RGBA')).astype(float)
RGB, A = img[..., :3], img[..., 3]
R, G, B = RGB[..., 0], RGB[..., 1], RGB[..., 2]
H, W = A.shape
rng = np.random.default_rng(7)

on = A > 128
lum = 0.3 * R + 0.59 * G + 0.11 * B
blue = on & (B > R + 15)

# Gold thread: warm colour, or clearly darker than the white satin around it.
ref = ndi.maximum_filter(ndi.gaussian_filter(np.where(on, lum, 0), 1), size=11)
goldness = np.clip(((R - B) - 40) / 40, 0, 1) + np.clip((ref - lum - 30) / 30, 0, 1)
goldness = np.where(on & ~blue, np.clip(goldness, 0, 1), 0)

# Thread direction: stitches run along the stripes, across the light gradient.
L = ndi.gaussian_filter(lum, 1.0)
gx, gy = ndi.sobel(L, 1), ndi.sobel(L, 0)
jxx, jyy, jxy = (ndi.gaussian_filter(v, 3.5) for v in (gx * gx, gy * gy, gx * gy))
grad_angle = 0.5 * np.arctan2(2 * jxy, jxx - jyy)
coherence = np.hypot(jxx - jyy, 2 * jxy) / (jxx + jyy + 1e-6)

# Disk: fit from the blue extent; clip to the photo's own blue shape.
ys, xs = np.where(blue)
DISK_R = (xs.max() - xs.min() + 1) / 2
DISK_X = (xs.max() + xs.min()) / 2
DISK_Y = ys.max() - DISK_R + 1


def thread_angle(x, y):
    """Stitch angle at (x, y): photo's thread direction, or radial where it is unclear."""
    xi, yi = int(x), int(y)
    radial = np.arctan2(y - DISK_Y, x - DISK_X)
    if coherence[yi, xi] < 0.25:
        return radial
    a = grad_angle[yi, xi] + np.pi / 2
    # pick the half-turn nearest radial so neighbouring stitches agree
    if np.cos(a - radial) < 0:
        a += np.pi
    return a


def trace(mask, smooth=0.9, tol=0.35):
    field = np.pad(ndi.gaussian_filter(mask.astype(float), smooth), 1)
    parts = []
    for c in measure.find_contours(field, 0.5):
        c = measure.approximate_polygon(c, tol)
        if len(c) >= 4:
            parts.append(catmull_rom(c[:, ::-1] - 1))
    return ' '.join(parts)


def catmull_rom(p):
    p = p[:-1] if np.allclose(p[0], p[-1]) else p
    n = len(p)
    d = [f'M{p[0][0]:.1f} {p[0][1]:.1f}']
    for i in range(n):
        p0, p1, p2, p3 = p[i - 1], p[i], p[(i + 1) % n], p[(i + 2) % n]
        c1, c2 = p1 + (p2 - p0) / 6, p2 - (p3 - p1) / 6
        d.append(f'C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}')
    return ''.join(d) + 'Z'


def hexcol(c):
    c = np.clip(c, 0, 255).astype(int)
    return f'#{c[0]:02x}{c[1]:02x}{c[2]:02x}'


# Colours sampled from a lightly smoothed photo so one noisy pixel doesn't decide a stitch.
smooth_rgb = np.dstack([ndi.gaussian_filter(RGB[..., i], 0.8) for i in range(3)])


def lay(mask, spacing, length, colour_fn, keep=lambda x, y: True):
    out = []
    for y0 in np.arange(0, H, spacing):
        for x0 in np.arange(0, W, spacing):
            x, y = x0 + rng.uniform(0, spacing), y0 + rng.uniform(0, spacing)
            xi, yi = int(x), int(y)
            if xi >= W or yi >= H or not mask[yi, xi] or not keep(x, y):
                continue
            a = thread_angle(x, y) + rng.normal(0, 0.08)
            l = length * rng.uniform(0.7, 1.3) / 2
            out.append(
                f'<line x1="{x - np.cos(a) * l:.1f}" y1="{y - np.sin(a) * l:.1f}" '
                f'x2="{x + np.cos(a) * l:.1f}" y2="{y + np.sin(a) * l:.1f}" '
                f'stroke="{colour_fn(xi, yi)}"/>'
            )
    return '\n'.join(out)


def white_colour(x, y):
    c = smooth_rgb[y, x]
    # nudge toward clean cream so the satin reads as thread, not photo noise
    c = 0.55 * c + 0.45 * np.array([244, 237, 224]) + rng.normal(0, 6)
    return hexcol(c)


def gold_colour(x, y):
    c = smooth_rgb[y, x]
    tone = np.array([196, 150, 92]) * rng.uniform(0.75, 1.15)
    return hexcol(0.4 * c + 0.6 * tone)


white_mask = on & ~ndi.binary_dilation(blue, iterations=1)
gold_mask = goldness > 0.6

white_lines = lay(white_mask, 3.1, 22, white_colour)
gold_lines = lay(gold_mask, 1.9, 7, gold_colour,
                 keep=lambda x, y: rng.random() < 0.2 + 0.8 * goldness[int(y), int(x)])

# Disk: radial satin in the photo's blue, light catching the upper-left threads.
base_blue = RGB[blue].mean(axis=0)
disk = []
for deg in np.arange(0, 360, 0.45):
    t = np.radians(deg + rng.normal(0, 0.12))
    light = 0.5 + 0.5 * np.cos(t - np.radians(-140))
    c = base_blue * (0.82 + 0.45 * light) * rng.uniform(0.93, 1.07)
    r0 = rng.uniform(0, 6)
    disk.append(
        f'<line x1="{DISK_X + np.cos(t) * r0:.1f}" y1="{DISK_Y + np.sin(t) * r0:.1f}" '
        f'x2="{DISK_X + np.cos(t) * (DISK_R + 2):.1f}" y2="{DISK_Y + np.sin(t) * (DISK_R + 2):.1f}" '
        f'stroke="{hexcol(c)}" stroke-width="1.5"/>'
    )
disk = '\n'.join(disk)
# Lower half is a true circle; the top half follows the photo, where thorax and shield overlap it.
yy, xx = np.mgrid[:H, :W]
circle = np.hypot(xx - DISK_X, yy - DISK_Y) <= DISK_R + 1
disk_shape = circle & (ndi.binary_dilation(blue, iterations=2) | (yy > DISK_Y))
disk_d = trace(disk_shape, smooth=1.0)
silhouette_d = trace(on, smooth=0.9)


def png_uri(arr, mode):
    buf = io.BytesIO()
    Image.fromarray(arr.astype(np.uint8), mode).save(buf, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


# Underlay: the photo, softened, fills any hairline gaps between stitches with the right colour.
# It is darkened a touch so the gaps between satin stitches read as grooves.
under = np.dstack([ndi.gaussian_filter(RGB[..., i], 1.2) * 0.7 for i in range(3)] + [A])
under_uri = png_uri(under, 'RGBA')

# Relief: only the photo's mid-scale light and shade (raised stitches, padding), not its pixels.
relief = ndi.gaussian_filter(lum, 1.4) - ndi.gaussian_filter(lum, 9)
relief = np.clip(relief * 1.6 + 128, 0, 255)
relief_uri = png_uri(np.dstack([relief, relief, relief, np.where(on, 255, 0)]), 'RGBA')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
  <clipPath id="clipMoth"><path d="{silhouette_d}" clip-rule="evenodd"/></clipPath>
  <clipPath id="clipDisk"><path d="{disk_d}" clip-rule="evenodd"/></clipPath>
</defs>
<image href="{under_uri}" width="{W}" height="{H}"/>
<g clip-path="url(#clipMoth)" stroke-linecap="round">
  <g stroke-width="2.25">
  {white_lines}
  </g>
  <g clip-path="url(#clipDisk)">
    <rect width="{W}" height="{H}" fill="{hexcol(base_blue * 0.85)}"/>
    {disk}
  </g>
  <g stroke-width="1.35">
  {gold_lines}
  </g>
</g>
<image href="{relief_uri}" width="{W}" height="{H}" style="mix-blend-mode:soft-light" opacity="0.55"/>
</svg>
'''
open(dst, 'w').write(svg)
print(f'disk r={DISK_R:.0f} at ({DISK_X:.0f},{DISK_Y:.0f}); '
      f'{svg.count("<line")} stitches; {len(svg) // 1024} KB')
