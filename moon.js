// Draws the live moon above the moth: today's phase, lit side turned the way it
// looks from where the viewer is, refreshed every minute so it drifts through the day.

// Wrapped so its names don't collide with clock.js, which shares the page's global scope.
(() => {
  const NS = 'http://www.w3.org/2000/svg';
  const MOON = { x: 476, y: 135, r: 92 }; // in moth.svg's coordinate space, centred over the moth
  const LOCATION_KEY = 'moon-location';

  const litPath = document.getElementById('moonLit');
  const label = document.getElementById('moonLabel');
  const sky = document.querySelector('.moon-sky');

  // --- embroidery: stitched once, then clipped to the lit part on every update ----

  let seed = 11;
  const rand = () => {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  };
  const GOLD = ['#c9a06a', '#b98a4e', '#d8b57f', '#a87a45', '#8f6638'];
  const SEED_GOLD = ['#e6c48a', '#f0d9a8', '#8f6638'];
  const pick = (list) => list[Math.floor(rand() * list.length)];

  function stitchMoon() {
    const g = document.getElementById('moonStitches');
    const frag = document.createDocumentFragment();
    const R = MOON.r;
    const point = () => {
      const r = R * Math.sqrt(rand()), a = rand() * 2 * Math.PI;
      return [Math.cos(a) * r, Math.sin(a) * r];
    };
    // couched stitches running around the disc, as on the crescent
    for (let i = 0; i < 2600; i++) {
      const [x, y] = point();
      const t = Math.atan2(y, x) + Math.PI / 2 + (rand() - 0.5);
      const l = 5 + rand() * 6;
      const s = document.createElementNS(NS, 'line');
      s.setAttribute('x1', x.toFixed(1));
      s.setAttribute('y1', y.toFixed(1));
      s.setAttribute('x2', (x + Math.cos(t) * l).toFixed(1));
      s.setAttribute('y2', (y + Math.sin(t) * l).toFixed(1));
      s.setAttribute('stroke', pick(GOLD));
      s.setAttribute('stroke-width', (2 + rand()).toFixed(2));
      frag.appendChild(s);
    }
    // seed stitches on top
    for (let i = 0; i < 700; i++) {
      const [x, y] = point();
      const c = document.createElementNS(NS, 'circle');
      c.setAttribute('cx', x.toFixed(1));
      c.setAttribute('cy', y.toFixed(1));
      c.setAttribute('r', (1 + rand() * 1.2).toFixed(1));
      c.setAttribute('fill', pick(SEED_GOLD));
      frag.appendChild(c);
    }
    g.appendChild(frag);
  }

  // --- shape of the lit part ----------------------------------------------------

  // Lit side facing right: the limb is a half circle, the terminator a half ellipse
  // whose width shrinks to nothing at the quarters and flips side at full/new.
  function litShape(fraction) {
    const R = MOON.r;
    const a = R * Math.abs(1 - 2 * fraction);
    const gibbous = fraction > 0.5 ? 1 : 0;
    return `M0 ${-R} A${R} ${R} 0 0 1 0 ${R} A${a.toFixed(2)} ${R} 0 0 ${gibbous} 0 ${-R} Z`;
  }

  // --- where the viewer is ------------------------------------------------------

  // Without a location, the hemisphere is enough to put the lit side on the right edge.
  // Guessed from the time zone; nothing leaves the device either way.
  const SOUTHERN_ZONES = /^(Australia|Antarctica)\/|^America\/(Argentina|Santiago|Sao_Paulo|Montevideo|Asuncion|La_Paz|Lima|Punta_Arenas)|^Pacific\/(Auckland|Chatham|Fiji|Tongatapu|Apia|Noumea|Efate|Tahiti|Port_Moresby|Rarotonga)|^Africa\/(Johannesburg|Maputo|Harare|Lusaka|Windhoek|Gaborone|Maseru|Mbabane|Lubumbashi|Luanda|Blantyre|Dar_es_Salaam)|^Indian\/(Antananarivo|Mauritius|Reunion|Mayotte)|^Asia\/(Jakarta|Makassar|Jayapura|Dili)|^Atlantic\/Stanley/;

  function guessSouthern() {
    try {
      return SOUTHERN_ZONES.test(Intl.DateTimeFormat().resolvedOptions().timeZone || '');
    } catch {
      return false;
    }
  }

  let place = null;
  try {
    place = JSON.parse(localStorage.getItem(LOCATION_KEY));
  } catch {
    place = null;
  }

  function askForLocation() {
    if (!('geolocation' in navigator)) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        // two decimals (about 1 km) is far finer than the moon's orientation needs
        place = { lat: +pos.coords.latitude.toFixed(2), lng: +pos.coords.longitude.toFixed(2) };
        try {
          localStorage.setItem(LOCATION_KEY, JSON.stringify(place));
        } catch {}
        render();
      },
      () => {}, // declined or unavailable: keep the time-zone guess
      { maximumAge: 6 * 3600 * 1000, timeout: 20000 }
    );
  }

  // --- drawing ------------------------------------------------------------------

  function render() {
    const now = new Date();
    const { fraction, phase, limbAngle } = MoonPhase.illumination(now);

    // Direction of the lit limb on screen, degrees clockwise from straight up.
    let litDirection;
    if (place) {
      const zenithAngle = limbAngle - MoonPhase.parallacticAngle(now, place.lat, place.lng);
      litDirection = (-zenithAngle * 180) / Math.PI;
    } else {
      const waxing = phase < 0.5;
      litDirection = waxing !== guessSouthern() ? 90 : 270;
    }

    litPath.setAttribute('d', litShape(fraction));
    litPath.setAttribute('transform', `rotate(${(litDirection - 90).toFixed(2)})`);

    const name = MoonPhase.phaseName(phase);
    const percent = Math.round(fraction * 100);
    label.textContent = `${name} · ${percent}%`;
    sky.setAttribute('aria-label', `Moon: ${name}, ${percent}% lit${place ? ', as seen from your location' : ''}`);
  }

  stitchMoon();
  render();
  askForLocation();
  setInterval(render, 60 * 1000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) render(); });
})();
