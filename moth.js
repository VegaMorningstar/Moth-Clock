// Builds the embroidery stitch by stitch, and sizes the carpet border to the window.

const NS = 'http://www.w3.org/2000/svg';

// Seeded so the stitches land in the same place on every load.
let seed = 7;
const rand = () => {
  seed = (seed * 16807) % 2147483647;
  return (seed - 1) / 2147483646;
};
const between = (a, b) => a + rand() * (b - a);
const pick = (list) => list[Math.floor(rand() * list.length)];

function el(tag, attrs, parent) {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.appendChild(node);
  return node;
}

const CREAM = ['#f4ede1', '#efe5d3', '#e8dcc6', '#f8f3ea', '#e2d4bb'];
const GOLD = ['#c9a06a', '#b98a4e', '#d8b57f', '#a87a45', '#8f6638'];
const rad = (deg) => (deg * Math.PI) / 180;

// Satin stitch: thread fanning out from the wing root, clipped to the wing.
function satin(group, clip, ox, oy, fromDeg, toDeg, step) {
  const g = el('g', { 'clip-path': `url(#${clip})` }, group);
  el('rect', { width: 1000, height: 1000, fill: '#ece2d0' }, g);
  for (let a = fromDeg; a <= toDeg; a += step) {
    const t = rad(a + between(-0.4, 0.4));
    el('line', {
      x1: ox, y1: oy,
      x2: ox + Math.cos(t) * 520, y2: oy + Math.sin(t) * 520,
      stroke: pick(CREAM), 'stroke-width': between(2, 3.2), 'stroke-linecap': 'round',
    }, g);
  }
  return g;
}

// Gold veins: running stitch along gently bowed lines, plus broken cross-veins.
function veins(g, ox, oy, angles, length, bow) {
  for (const a of angles) {
    const t = rad(a);
    const len = length * between(0.85, 1.05);
    const ex = ox + Math.cos(t) * len, ey = oy + Math.sin(t) * len;
    const mx = ox + Math.cos(t) * len * 0.5 - Math.sin(t) * bow;
    const my = oy + Math.sin(t) * len * 0.5 + Math.cos(t) * bow;
    el('path', {
      d: `M${ox + Math.cos(t) * 40} ${oy + Math.sin(t) * 40} Q${mx} ${my} ${ex} ${ey}`,
      fill: 'none', stroke: pick(GOLD.slice(1)), 'stroke-width': between(3, 4.4),
      'stroke-dasharray': `${between(6, 10)} ${between(2, 4)}`, 'stroke-linecap': 'round',
    }, g);
  }
  for (let i = 0; i < 220; i++) {
    const t = rad(between(Math.min(...angles) - 25, Math.max(...angles) + 25));
    const r = between(60, length * 1.05);
    const x = ox + Math.cos(t) * r, y = oy + Math.sin(t) * r, l = between(6, 16);
    el('line', {
      x1: x, y1: y, x2: x + Math.cos(t) * l, y2: y + Math.sin(t) * l,
      stroke: pick(GOLD), 'stroke-width': between(1.4, 2.2), 'stroke-linecap': 'round', opacity: between(0.5, 0.9),
    }, g);
  }
  const lo = Math.min(...angles), hi = Math.max(...angles);
  for (const r of [length * 0.34, length * 0.5, length * 0.66, length * 0.82]) {
    for (let a = lo; a < hi; a += between(9, 18)) {
      if (rand() < 0.15) continue;
      const a1 = rad(a), a2 = rad(a + between(5, 12));
      const r1 = r * between(0.92, 1.08), r2 = r * between(0.92, 1.08);
      el('path', {
        d: `M${ox + Math.cos(a1) * r1} ${oy + Math.sin(a1) * r1} Q${ox + Math.cos((a1 + a2) / 2) * r * 1.06} ${oy + Math.sin((a1 + a2) / 2) * r * 1.06} ${ox + Math.cos(a2) * r2} ${oy + Math.sin(a2) * r2}`,
        fill: 'none', stroke: pick(GOLD), 'stroke-width': between(2.2, 3.2),
        'stroke-dasharray': '5 2.5', 'stroke-linecap': 'round',
      }, g);
    }
  }
}

// Gold-dusted margin: a ragged outline plus short hatch stitches pointing inward.
function edge(group, pathId, clip, ox, oy) {
  const src = document.getElementById(pathId);
  const g = el('g', { 'clip-path': `url(#${clip})` }, group);
  el('use', {
    href: `#${pathId}`, fill: 'none', stroke: '#b98a4e', 'stroke-width': 9, filter: 'url(#ragged)',
  }, g);
  const total = src.getTotalLength();
  for (let s = 0; s < total; s += between(3.5, 6)) {
    const p = src.getPointAtLength(s);
    const dx = ox - p.x, dy = oy - p.y, d = Math.hypot(dx, dy);
    const len = between(8, rand() < 0.2 ? 46 : 24);
    el('line', {
      x1: p.x, y1: p.y, x2: p.x + (dx / d) * len, y2: p.y + (dy / d) * len,
      stroke: pick(GOLD), 'stroke-width': between(1.4, 2.6), 'stroke-linecap': 'round',
      opacity: between(0.7, 1),
    }, g);
  }
}

function buildWing() {
  const wing = document.getElementById('wingR');

  // hindwing first so the forewing overlaps it
  satin(wing, 'clipHind', 512, 690, -20, 120, 0.7);
  const hv = el('g', { 'clip-path': 'url(#clipHind)' }, wing);
  veins(hv, 512, 690, [8, 30, 52, 74, 96], 230, 14);
  edge(wing, 'hindR', 'clipHind', 560, 760);

  satin(wing, 'clipFore', 516, 660, -95, 30, 0.45);
  const fv = el('g', { 'clip-path': 'url(#clipFore)' }, wing);
  veins(fv, 516, 660, [-38, -26, -15, -5, 4, 13, 21], 440, -18);
  edge(wing, 'foreR', 'clipFore', 640, 680);

  // a soft seam where fore and hind wings meet
  el('use', { href: '#foreR', fill: 'none', stroke: '#8f6638', 'stroke-width': 2.4, opacity: 0.8 }, wing);
}

function buildThorax() {
  const g = document.getElementById('thoraxStitches');
  for (let y = 566; y < 640; y += 3.2) {
    const half = Math.sqrt(Math.max(0, 1 - ((y - 602) / 40) ** 2)) * 42;
    el('line', {
      x1: 500 - half, y1: y + between(-1, 1), x2: 500 + half, y2: y + between(-1, 1),
      stroke: pick(CREAM), 'stroke-width': 2.6, 'stroke-linecap': 'round',
    }, g);
  }
  // gold flecks on the head
  for (let i = 0; i < 26; i++) {
    const a = rand() * Math.PI * 2, r = between(8, 36);
    const x = 500 + Math.cos(a) * r, y = 598 + Math.sin(a) * r * 0.9;
    el('line', { x1: x, y1: y, x2: x + between(-5, 5), y2: y + between(3, 8), stroke: pick(GOLD), 'stroke-width': 2, 'stroke-linecap': 'round' }, g);
  }
}

function buildAntennae() {
  const g = document.getElementById('antennae');
  for (const side of [-1, 1]) {
    const x0 = 500 + side * 14, y0 = 572;
    const x1 = 500 + side * 40, y1 = 528;
    const x2 = 500 + side * 92, y2 = 492;
    el('path', { d: `M${x0} ${y0} Q${x1} ${y1} ${x2} ${y2}`, 'stroke-width': 4 }, g);
    // feathered barbs along the outer half
    for (let t = 0.35; t <= 1; t += 0.07) {
      const bx = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * x1 + t * t * x2;
      const by = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * y1 + t * t * y2;
      const len = 6 + 14 * Math.sin(t * Math.PI);
      el('line', { x1: bx, y1: by, x2: bx + side * len * 0.35, y2: by - len, 'stroke-width': 2.4 }, g);
      el('line', { x1: bx, y1: by, x2: bx + side * len, y2: by + len * 0.15, 'stroke-width': 2.4 }, g);
    }
  }
}

function buildDisk() {
  const g = document.getElementById('disk');
  const cx = 500, cy = 708, R = 104;
  el('circle', { cx, cy, r: R, fill: 'url(#satinBlue)' }, g);
  // radial satin stitch; the light catches threads facing upper-left
  for (let a = 0; a < 360; a += 0.9) {
    const t = rad(a + between(-0.3, 0.3));
    const light = 0.5 + 0.5 * Math.cos(t - rad(-120));
    const l = 18 + light * 20 + between(-3, 3);
    el('line', {
      x1: cx + Math.cos(t) * between(0, 6), y1: cy + Math.sin(t) * between(0, 6),
      x2: cx + Math.cos(t) * R, y2: cy + Math.sin(t) * R,
      stroke: `hsl(${between(220, 226)} 68% ${l}%)`, 'stroke-width': 2.6, 'stroke-linecap': 'round',
    }, g);
  }
  el('circle', { cx, cy, r: R - 1, fill: 'none', stroke: '#0a1a4d', 'stroke-width': 2.5 }, g);

  // gold abdomen marking at the top of the disk
  const mark = el('g', {}, g);
  el('path', { d: 'M500 640 L532 668 L516 700 L500 716 L484 700 L468 668 Z', fill: '#c9a06a' }, mark);
  for (let i = 0; i < 40; i++) {
    const x = between(474, 526), y = between(648, 708);
    if (Math.abs(x - 500) > (y < 668 ? (y - 640) * 1.15 : 32 - (y - 668) * 0.66)) continue;
    el('line', { x1: x, y1: y, x2: x + between(-4, 4), y2: y + between(3, 7), stroke: pick(['#efe5d3', '#e6c48a', '#8f6638']), 'stroke-width': 2, 'stroke-linecap': 'round' }, mark);
  }
}

function buildCrescent() {
  const g = document.getElementById('crescent');
  // diagonal satin stitches across the crescent, then a scatter of seed stitches
  for (let i = 0; i < 900; i++) {
    const a = rand() * Math.PI, r = between(84, 120);
    const x = 500 + Math.cos(a) * r, y = 220 + Math.sin(a) * r, t = a + Math.PI / 2 + between(-0.5, 0.5);
    const l = between(5, 11);
    el('line', { x1: x, y1: y, x2: x + Math.cos(t) * l, y2: y + Math.sin(t) * l, stroke: pick(GOLD), 'stroke-width': between(2, 3), 'stroke-linecap': 'round' }, g);
  }
  for (let i = 0; i < 260; i++) {
    const a = rand() * Math.PI, r = between(70, 118);
    const x = 500 + Math.cos(a) * r, y = 220 + Math.sin(a) * r;
    el('circle', { cx: x, cy: y, r: between(1, 2.2), fill: pick(['#e6c48a', '#f0d9a8', '#8f6638']) }, g);
  }
}

// Carpet border, inset from the window edge.
function sizeBorder() {
  const w = window.innerWidth, h = window.innerHeight;
  const inset = Math.max(14, Math.min(w, h) * 0.035);
  const band = Math.max(36, Math.min(w, h) * 0.06);
  const set = (id, i) => {
    const r = document.getElementById(id);
    r.setAttribute('x', i); r.setAttribute('y', i);
    r.setAttribute('width', Math.max(0, w - i * 2)); r.setAttribute('height', Math.max(0, h - i * 2));
  };
  set('bandOuter', inset);
  set('bandInner', inset + band);
  const o = inset, i = inset + band;
  document.getElementById('bandFill').setAttribute('d',
    `M${o} ${o} H${w - o} V${h - o} H${o} Z M${i} ${i} V${h - i} H${w - i} V${i} Z`);
}

buildWing();
buildThorax();
buildAntennae();
buildDisk();
buildCrescent();
sizeBorder();
window.addEventListener('resize', sizeBorder);
