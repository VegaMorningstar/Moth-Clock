# Builds moth.svg: clean vector embroidery in the shape of the photo cutout.
#
# Only shapes come from the photo: the moth's silhouette, the crescent, the shield
# on the disk, and the centre lines of the gold veins. Everything inside them is
# drawn fresh as crisp satin, running-stitch veins and gold hatching.
#
# Usage: python tools/build_moth.py source/moth-cutout.png moth.svg

import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure, morphology

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
moon = on & (yy < SPLIT)
moon = ndi.binary_fill_holes(ndi.binary_closing(moon, iterations=5))
moon = ndi.binary_opening(moon, iterations=2)

ys, xs = np.where(blue)
DISK_R = (xs.max() - xs.min() + 1) / 2
DISK_X = (xs.max() + xs.min()) / 2
DISK_Y = ys.max() - DISK_R + 1
circle = np.hypot(xx - DISK_X, yy - DISK_Y) <= DISK_R + 1
# Lower half is a true circle; the top half follows the photo, where thorax and shield overlap it.
disk = circle & (ndi.binary_dilation(blue, iterations=2) | (yy > DISK_Y))

# The shield is the gold shape cut into the top of the disk: inside the blue's outline but not blue.
shield = morphology.convex_hull_image(blue) & ~ndi.binary_dilation(blue, iterations=1)
lab, n = ndi.label(shield)
shield = lab == (np.argmax(ndi.sum(shield, lab, range(1, n + 1))) + 1)
shield = ndi.binary_fill_holes(ndi.binary_opening(shield, iterations=2))

# Antennae: the thin parts of the silhouette above the thorax.
thick = ndi.binary_opening(moth, structure=np.ones((15, 15)))
antennae = moth & ~ndi.binary_dilation(thick, iterations=2) & (yy < DISK_Y - DISK_R)

# Gold veins: thread clearly darker or warmer than the white satin around it.
ref = ndi.maximum_filter(ndi.gaussian_filter(np.where(on, lum, 0), 1), size=11)
gold = moth & ~blue & (((R - B) > 62) | ((ref - lum) > 40))
gold = ndi.binary_opening(ndi.gaussian_filter(gold.astype(float), 1.2) > 0.5)
interior = ndi.binary_erosion(moth & ~disk & ~antennae, iterations=9)
veins_skel = morphology.skeletonize(gold & interior)


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


def skeleton_paths(skel, min_len=18):
    """Walk a 1-px skeleton into polylines, splitting at junctions."""
    pts = set(zip(*np.where(skel)))
    nbrs = lambda p: [(p[0] + dy, p[1] + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                      if (dy or dx) and (p[0] + dy, p[1] + dx) in pts]
    degree = {p: len(nbrs(p)) for p in pts}
    seen, paths = set(), []
    starts = sorted(p for p in pts if degree[p] != 2) + sorted(pts)
    for s in starts:
        for nb in nbrs(s):
            if (s, nb) in seen:
                continue
            line_, prev, cur = [s], s, nb
            seen.add((s, nb))
            while True:
                seen.add((cur, prev))
                line_.append(cur)
                nxt = [q for q in nbrs(cur) if q != prev and (cur, q) not in seen]
                if degree[cur] != 2 or not nxt:
                    break
                seen.add((cur, nxt[0]))
                prev, cur = cur, nxt[0]
            arr = np.array(line_, float)[:, ::-1]
            span = np.hypot(*(arr[-1] - arr[0]))
            # keep vein-like runs; drop the squiggles left by stitch texture
            if len(line_) >= min_len and span > 0.62 * len(line_):
                paths.append(measure.approximate_polygon(arr, 2.0))
    return paths


# --- drawing ------------------------------------------------------------------

CREAM = ['#f4ede1', '#efe5d3', '#e8dcc6', '#f8f3ea', '#e2d4bb']
GOLD = ['#c9a06a', '#b98a4e', '#d8b57f', '#a87a45', '#8f6638']
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

# Veins: running stitch along the photo's vein lines.
vein_paths = skeleton_paths(veins_skel)
veins = []
for p in vein_paths:
    veins.append(f'<path d="{spline(p, closed=False)}" stroke="{pick(["#b98a4e", "#a87a45", "#8f6638"])}" '
                 f'stroke-width="{rng.uniform(3, 4.2):.2f}" '
                 f'stroke-dasharray="{rng.uniform(6, 9):.1f} {rng.uniform(2, 3.5):.1f}"/>')

# Sketchy gold hatching through the wings, denser where the photo has gold.
hatch = []
gold_soft = ndi.gaussian_filter(gold.astype(float), 3)
cand = np.argwhere(moth & ~disk & ~antennae)
for y, x in cand[rng.choice(len(cand), 2600, replace=False)]:
    if rng.random() > 0.15 + 0.85 * gold_soft[y, x]:
        continue
    t = np.arctan2(y - DISK_Y, x - DISK_X) + rng.normal(0, 0.15)
    l = rng.uniform(5, 13)
    hatch.append(line(x, y, x + np.cos(t) * l, y + np.sin(t) * l, pick(GOLD), rng.uniform(1.3, 2.1),
                      f' opacity="{rng.uniform(0.55, 0.95):.2f}"'))

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
        far = np.clip((d - DISK_R) / 300, 0, 1)
        l = rng.uniform(6, 14 + 30 * far)
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


shield_flecks = flecks(shield, 60, ['#efe5d3', '#e6c48a', '#8f6638'])
antenna_flecks = flecks(antennae, 90, ['#e6c48a', '#8f6638', '#d8b57f'], (2, 5))

# Crescent: dense couched stitches across the band, then seed stitches.
pts = np.argwhere(moon)
MC = np.array([pts[:, 1].mean(), pts[:, 0].min() - 30])
moon_lines = []
for y, x in pts[rng.choice(len(pts), 1400, replace=False)]:
    t = np.arctan2(y - MC[1], x - MC[0]) + np.pi / 2 + rng.uniform(-0.5, 0.5)
    l = rng.uniform(5, 11)
    moon_lines.append(line(x, y, x + np.cos(t) * l, y + np.sin(t) * l, pick(GOLD), rng.uniform(2, 3)))
for y, x in pts[rng.choice(len(pts), 380, replace=False)]:
    moon_lines.append(f'<circle cx="{x}" cy="{y}" r="{rng.uniform(1, 2.2):.1f}" '
                      f'fill="{pick(["#e6c48a", "#f0d9a8", "#8f6638"])}"/>')

wing_d = trace(moth & ~antennae)
disk_d = trace(disk)
shield_d = trace(shield, smooth=1.2)
ant_d = trace(antennae, smooth=0.8)
moon_d = trace(moon, smooth=1.5)
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
  <clipPath id="clipWing"><path d="{wing_d}"/></clipPath>
  <clipPath id="clipDisk"><path d="{disk_d}"/></clipPath>
  <clipPath id="clipShield"><path d="{shield_d}"/></clipPath>
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
    {J(veins)}
    {J(hatch)}
    <path d="{wing_d}" stroke="#b98a4e" stroke-width="9" filter="url(#ragged)"/>
    {J(edge)}
  </g>

  <g clip-path="url(#clipDisk)">
    <path d="{disk_d}" fill="url(#satinBlue)"/>
    {J(disk_lines)}
    <circle cx="{DISK_X:.1f}" cy="{DISK_Y:.1f}" r="{DISK_R - 0.5:.1f}" stroke="#0a1a4d" stroke-width="2.5"/>
  </g>

  <g clip-path="url(#clipShield)">
    <path d="{shield_d}" fill="#c9a06a"/>
    {J(shield_flecks)}
  </g>
</g>
</svg>
'''
open(dst, 'w').write(svg)
print(f'{len(vein_paths)} veins; {svg.count("<line")} stitches; {len(svg) // 1024} KB')
