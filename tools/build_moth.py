# Builds moth.svg: clean vector embroidery in the shape of the photo cutout.
#
# Only the moth's shape comes from the photo: its silhouette, antennae and the gold
# pattern on the wings (veins and gold-dusted margins). The crescent and the disk are the original geometric
# designs, sized and placed where the photo has them. Everything inside them is
# drawn fresh as crisp satin, gold stitching and gold edging.
#
# Usage: python tools/build_moth.py source/moth-cutout.png moth.svg

import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure

src, dst = sys.argv[1], sys.argv[2]
img = np.asarray(Image.open(src).convert('RGBA')).astype(float)
R, G, B, A = (img[..., i] for i in range(4))
H, W = A.shape
rng = np.random.default_rng(7)
yy, xx = np.mgrid[:H, :W]

on = A > 128
lum = 0.3 * R + 0.59 * G + 0.11 * B
blue = on & (B > R + 15)

# --- shapes from the photo ----------------------------------------------------

rows = np.where(on.any(axis=1))[0]
gap = np.where(np.diff(rows) > 20)[0]
SPLIT = rows[gap[0]] + 10  # crescent above, moth below

moth = on & (yy >= SPLIT)
moth = ndi.binary_fill_holes(ndi.binary_closing(moth, iterations=2))
# Crescent: a clean geometric crescent, sized and placed where the photo's one sits.
mp = np.argwhere(on & (yy < SPLIT))
MOON_R = (mp[:, 1].max() - mp[:, 1].min()) / 2 * 1.02
MOON_X = (mp[:, 1].max() + mp[:, 1].min()) / 2
MOON_Y = mp[:, 0].max() - MOON_R
INNER_R, INNER_DY = MOON_R * 0.932, MOON_R * 0.254  # proportions of the first design
moon = ((np.hypot(xx - MOON_X, yy - MOON_Y) <= MOON_R)
        & (np.hypot(xx - MOON_X, yy - MOON_Y + INNER_DY) > INNER_R))

ys, xs = np.where(blue)
DISK_R = (xs.max() - xs.min() + 1) / 2
DISK_X = (xs.max() + xs.min()) / 2
DISK_Y = ys.max() - DISK_R + 1
circle = np.hypot(xx - DISK_X, yy - DISK_Y) <= DISK_R + 1
disk = circle

# Antennae: the thin parts of the silhouette above the thorax.
thick = ndi.binary_opening(moth, structure=np.ones((15, 15)))
antennae = moth & ~ndi.binary_dilation(thick, iterations=2) & (yy < DISK_Y - DISK_R)

# Gold pattern: wherever the photo's thread is warm gold, or clearly darker than the
# white satin around it. This is the veining and gold-dusted margin of the photo.
ref = ndi.maximum_filter(ndi.gaussian_filter(np.where(on, lum, 0), 1), size=11)
goldness = np.clip(((R - B) - 40) / 40, 0, 1) + np.clip((ref - lum - 30) / 30, 0, 1)
gold = moth & ~disk & ~antennae & (ndi.gaussian_filter(np.clip(goldness, 0, 1), 0.7) > 0.55)
lab, n = ndi.label(gold)
gold = np.isin(lab, np.where(ndi.sum(gold, lab, range(1, n + 1)) > 5)[0] + 1)

# Thread direction in the photo: gold stitches run along the stripes, across the light gradient.
L = ndi.gaussian_filter(lum, 1.0)
gx, gy = ndi.sobel(L, 1), ndi.sobel(L, 0)
jxx, jyy, jxy = (ndi.gaussian_filter(v, 3.5) for v in (gx * gx, gy * gy, gx * gy))
grad_angle = 0.5 * np.arctan2(2 * jxy, jxx - jyy)
coherence = np.hypot(jxx - jyy, 2 * jxy) / (jxx + jyy + 1e-6)


def thread_angle(x, y):
    radial = np.arctan2(y - DISK_Y, x - DISK_X)
    if coherence[int(y), int(x)] < 0.25:
        return radial
    a = grad_angle[int(y), int(x)] + np.pi / 2
    return a + np.pi if np.cos(a - radial) < 0 else a


def trace(mask, smooth=1.0, tol=0.4):
    field = np.pad(ndi.gaussian_filter(mask.astype(float), smooth), 1)
    parts = []
    for c in measure.find_contours(field, 0.5):
        c = measure.approximate_polygon(c, tol)
        if len(c) >= 4:
            parts.append(spline(c[:, ::-1] - 1, closed=True))
    return ' '.join(parts)


def spline(p, closed):
    """Catmull-Rom through points -> cubic Bezier path data."""
    if closed and np.allclose(p[0], p[-1]):
        p = p[:-1]
    n = len(p)
    get = (lambda i: p[i % n]) if closed else (lambda i: p[min(max(i, 0), n - 1)])
    d = [f'M{p[0][0]:.1f} {p[0][1]:.1f}']
    for i in range(n if closed else n - 1):
        p0, p1, p2, p3 = get(i - 1), get(i), get(i + 1), get(i + 2)
        c1, c2 = p1 + (p2 - p0) / 6, p2 - (p3 - p1) / 6
        d.append(f'C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}')
    return ''.join(d) + ('Z' if closed else '')



# --- drawing ------------------------------------------------------------------

CREAM = ['#f4ede1', '#efe5d3', '#e8dcc6', '#f8f3ea', '#e2d4bb']
GOLD = ['#c9a06a', '#b98a4e', '#d8b57f', '#a87a45', '#8f6638']
GOLD_DEEP = ['#c9a06a', '#b98a4e', '#a87a45', '#8f6638', '#7d5a33']  # the photo's gold is a shade browner
pick = lambda c: c[rng.integers(len(c))]


def line(x1, y1, x2, y2, stroke, width, extra=''):
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{width:.2f}"{extra}/>')


# Satin: long threads fanning out from the body, clipped to the wings.
satin = []
my_, mx_ = np.where(moth)
reach = np.hypot(mx_ - DISK_X, my_ - DISK_Y).max() + 10
for deg in np.arange(0, 360, 0.32):
    t = np.radians(deg + rng.uniform(-0.15, 0.15))
    satin.append(line(DISK_X, DISK_Y, DISK_X + np.cos(t) * reach, DISK_Y + np.sin(t) * reach,
                      pick(CREAM), rng.uniform(1.6, 2.6)))

# Gold pattern: crisp short stitches laid along the photo's thread, clipped to the traced gold shapes.
gold_lines = []
fill = ndi.binary_dilation(gold, iterations=1)
for y0 in np.arange(0, H, 2.3):
    for x0 in np.arange(0, W, 2.3):
        x, y = x0 + rng.uniform(0, 2.3), y0 + rng.uniform(0, 2.3)
        if int(x) >= W or int(y) >= H or not fill[int(y), int(x)]:
            continue
        t = thread_angle(x, y) + rng.normal(0, 0.1)
        l = rng.uniform(3, 5)
        gold_lines.append(line(x - np.cos(t) * l, y - np.sin(t) * l, x + np.cos(t) * l, y + np.sin(t) * l,
                               pick(GOLD_DEEP), rng.uniform(1.4, 2)))

# Gold-dusted margin: short stitches pointing in from the edge, longer toward the tips.
edge = []
body = ndi.gaussian_filter((moth & ~antennae).astype(float), 1)
for c in measure.find_contours(np.pad(body, 1), 0.5):
    c = c[:, ::-1] - 1
    pos = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(c, axis=0).T))])
    for s in np.arange(0, pos[-1], 4.2):
        x, y = c[min(np.searchsorted(pos, s), len(c) - 1)]
        dx, dy = DISK_X - x, DISK_Y - y
        d = np.hypot(dx, dy)
        l = rng.uniform(4, 10)
        edge.append(line(x, y, x + dx / d * l, y + dy / d * l, pick(GOLD), rng.uniform(1.4, 2.6),
                         f' opacity="{rng.uniform(0.7, 1):.2f}"'))

# Disk: radial satin, light catching the threads at upper left.
disk_lines = []
for deg in np.arange(0, 360, 0.9):
    t = np.radians(deg + rng.uniform(-0.3, 0.3))
    light = 0.5 + 0.5 * np.cos(t - np.radians(-120))
    l = 18 + light * 20 + rng.uniform(-3, 3)
    r0 = rng.uniform(0, 6)
    disk_lines.append(line(DISK_X + np.cos(t) * r0, DISK_Y + np.sin(t) * r0,
                           DISK_X + np.cos(t) * (DISK_R + 2), DISK_Y + np.sin(t) * (DISK_R + 2),
                           f'hsl({rng.uniform(220, 226):.0f} 68% {l:.0f}%)', 2.6))


def flecks(mask, count, colours, length=(3, 8)):
    pts = np.argwhere(mask)
    return [line(x, y, x + rng.uniform(-4, 4), y + rng.uniform(*length), pick(colours), 2)
            for y, x in pts[rng.choice(len(pts), min(count, len(pts)), replace=False)]]


antenna_flecks = flecks(antennae, 90, ['#e6c48a', '#8f6638', '#d8b57f'], (2, 5))

# Crescent: dense couched stitches along the curve, then seed stitches.
pts = np.argwhere(moon)
moon_lines = []
for y, x in pts[rng.choice(len(pts), 1400, replace=False)]:
    t = np.arctan2(y - MOON_Y, x - MOON_X) + np.pi / 2 + rng.uniform(-0.5, 0.5)
    l = rng.uniform(5, 11)
    moon_lines.append(line(x, y, x + np.cos(t) * l, y + np.sin(t) * l, pick(GOLD), rng.uniform(2, 3)))
for y, x in pts[rng.choice(len(pts), 380, replace=False)]:
    moon_lines.append(f'<circle cx="{x}" cy="{y}" r="{rng.uniform(1, 2.2):.1f}" '
                      f'fill="{pick(["#e6c48a", "#f0d9a8", "#8f6638"])}"/>')

wing_d = trace(moth & ~antennae)
gold_d = trace(gold, smooth=0.6, tol=0.3)
disk_d = (f'M{DISK_X - DISK_R:.1f} {DISK_Y:.1f}a{DISK_R:.1f} {DISK_R:.1f} 0 1 0 {2 * DISK_R:.1f} 0'
          f'a{DISK_R:.1f} {DISK_R:.1f} 0 1 0 {-2 * DISK_R:.1f} 0Z')
ant_d = trace(antennae, smooth=0.8)
# Horns are where the two circles cross.
hy = MOON_Y - (MOON_R ** 2 - INNER_R ** 2 + INNER_DY ** 2) / (2 * INNER_DY)
hx = np.sqrt(MOON_R ** 2 - (hy - MOON_Y) ** 2)
moon_d = (f'M{MOON_X - hx:.1f} {hy:.1f}A{MOON_R:.1f} {MOON_R:.1f} 0 1 0 {MOON_X + hx:.1f} {hy:.1f}'
          f'A{INNER_R:.1f} {INNER_R:.1f} 0 1 1 {MOON_X - hx:.1f} {hy:.1f}Z')
J = '\n'.join

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
  <!-- Raised embroidery: stitches sit proud of the velvet and catch a little light -->
  <filter id="thread" x="-5%" y="-5%" width="110%" height="110%">
    <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="2.2" result="d"/>
    <feGaussianBlur in="d" stdDeviation="0.35" result="soft"/>
    <feDropShadow in="soft" dx="0" dy="2.5" stdDeviation="2.5" flood-color="#200005" flood-opacity="0.65"/>
  </filter>
  <filter id="ragged" x="-5%" y="-5%" width="110%" height="110%">
    <feTurbulence type="fractalNoise" baseFrequency="0.25" numOctaves="2" seed="8" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="5"/>
  </filter>
  <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#e6c48a"/>
    <stop offset="50%" stop-color="#b98a4e"/>
    <stop offset="100%" stop-color="#8a6236"/>
  </linearGradient>
  <radialGradient id="satinBlue" cx="50%" cy="38%" r="60%">
    <stop offset="0%" stop-color="#2b4fa8"/>
    <stop offset="60%" stop-color="#16348a"/>
    <stop offset="100%" stop-color="#0c1f5c"/>
  </radialGradient>
  <clipPath id="clipGold"><path d="{gold_d}"/></clipPath>
  <clipPath id="clipWing"><path d="{wing_d}"/></clipPath>
  <clipPath id="clipDisk"><path d="{disk_d}"/></clipPath>
  <clipPath id="clipAnt"><path d="{ant_d}"/></clipPath>
  <clipPath id="clipMoon"><path d="{moon_d}"/></clipPath>
</defs>

<g filter="url(#thread)" stroke-linecap="round" fill="none">
  <g clip-path="url(#clipMoon)">
    <path d="{moon_d}" fill="url(#gold)"/>
    {J(moon_lines)}
  </g>

  <g clip-path="url(#clipAnt)">
    <path d="{ant_d}" fill="url(#gold)"/>
    {J(antenna_flecks)}
  </g>

  <g clip-path="url(#clipWing)">
    <path d="{wing_d}" fill="#ece2d0"/>
    {J(satin)}
    <g clip-path="url(#clipGold)">
      <path d="{gold_d}" fill="#8f6638"/>
      {J(gold_lines)}
    </g>
    <path d="{wing_d}" stroke="#b98a4e" stroke-width="9" filter="url(#ragged)"/>
    {J(edge)}
  </g>

  <g clip-path="url(#clipDisk)">
    <path d="{disk_d}" fill="url(#satinBlue)"/>
    {J(disk_lines)}
    <circle cx="{DISK_X:.1f}" cy="{DISK_Y:.1f}" r="{DISK_R - 0.5:.1f}" stroke="#0a1a4d" stroke-width="2.5"/>
  </g>
</g>
</svg>
'''
open(dst, 'w').write(svg)
print(f'{svg.count("<line")} stitches; {len(svg) // 1024} KB')
