# Cuts the moth and crescent out of the reference photo onto a transparent background.
# Usage: python tools/cut_photo.py <photo.png> source/moth-cutout.png
import sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

im = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(float)
R, G, B = im[..., 0], im[..., 1], im[..., 2]
# Velvet is strongly red (G and B well below R); thread is white, gold or blue.
ratio = np.maximum(G, B) / np.maximum(R, 1)
soft = np.clip((ratio - 0.40) / (0.62 - 0.40), 0, 1)

# Only the centre moth and crescent, not the neighbours cut off at the edges.
region = np.zeros(R.shape, bool)
region[150:1000, 110:1075] = True
region[:400, 900:] = False
region[:400, :300] = False
core = (soft > 0.6) & region
core = ndi.binary_closing(core, iterations=3)
core = ndi.binary_fill_holes(core)
lab, n = ndi.label(core)
sizes = ndi.sum(core, lab, range(1, n + 1))
keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 400])
keep = ndi.binary_fill_holes(ndi.binary_closing(keep, iterations=4))

# The crescent's gold is darker and speckled, so it gets a looser threshold of its own.
moon = np.zeros(R.shape, bool)
moon[155:410, 450:765] = True
soft2 = np.clip((ratio - 0.27) / (0.45 - 0.27), 0, 1)
mc = (soft2 > 0.5) & moon
mc = ndi.binary_opening(mc, iterations=1)
mc = ndi.binary_closing(mc, iterations=6)
mc = ndi.binary_fill_holes(mc)
lab2, n2 = ndi.label(mc)
s2 = ndi.sum(mc, lab2, range(1, n2 + 1))
mc = np.isin(lab2, [i + 1 for i, v in enumerate(s2) if v > 1500])
keep = (keep & ~moon) | mc
soft = np.where(moon, soft2, soft)

# Solid inside, soft fringe at the edge so stray fibres blend into the new velvet.
inner = ndi.binary_erosion(keep, iterations=2)
near = ndi.binary_dilation(keep, iterations=2)
alpha = np.where(inner, 1.0, np.where(near, soft, 0.0))
alpha = np.where(moon, np.where(near, np.clip(soft2 * 1.3, 0, 1), 0), alpha)
alpha = ndi.gaussian_filter(alpha, 0.6) * near

# Pull the red velvet out of fringe pixels so no pink halo is left behind.
velvet = np.array([128, 22, 30], float)
a = np.clip(alpha, 0.05, 1)[..., None]
rgb = np.where(alpha[..., None] < 0.98, (im - (1 - a) * velvet) / a, im)
rgb = np.clip(rgb, 0, 255)

ys, xs = np.where(alpha > 0.02)
y0, y1, x0, x1 = ys.min() - 4, ys.max() + 5, xs.min() - 4, xs.max() + 5
out = np.dstack([rgb, alpha * 255])[y0:y1, x0:x1].astype(np.uint8)
Image.fromarray(out, 'RGBA').save(sys.argv[2], optimize=True)
print('crop', x0, y0, x1, y1, 'components kept', len([s for s in sizes if s > 400]))
