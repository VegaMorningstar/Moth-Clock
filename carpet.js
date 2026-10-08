// Sizes the carpet border to the window.

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

sizeBorder();
window.addEventListener('resize', sizeBorder);
