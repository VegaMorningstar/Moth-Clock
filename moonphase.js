// Moon phase and orientation, calculated on the device.
//
// Low-precision Sun and Moon positions (the formulas from Meeus' "Astronomical
// Algorithms" as simplified on aa.quae.nl, the same ones SunCalc uses). Phase and
// illumination come out within a few hours of observatory tables, which is
// finer than anything visible in the drawing.

(function (root) {
  const RAD = Math.PI / 180;
  const OBLIQUITY = RAD * 23.4397;
  const DAY_MS = 86400000;
  const J2000 = 2451545;
  const SUN_DISTANCE_KM = 149598000;

  const daysSinceJ2000 = (date) => date.valueOf() / DAY_MS + 2440587.5 - J2000;

  const rightAscension = (l, b) =>
    Math.atan2(Math.sin(l) * Math.cos(OBLIQUITY) - Math.tan(b) * Math.sin(OBLIQUITY), Math.cos(l));
  const declination = (l, b) =>
    Math.asin(Math.sin(b) * Math.cos(OBLIQUITY) + Math.cos(b) * Math.sin(OBLIQUITY) * Math.sin(l));

  function sun(d) {
    const M = RAD * (357.5291 + 0.98560028 * d);
    const C = RAD * (1.9148 * Math.sin(M) + 0.02 * Math.sin(2 * M) + 0.0003 * Math.sin(3 * M));
    const L = M + C + RAD * 102.9372 + Math.PI; // ecliptic longitude
    return { ra: rightAscension(L, 0), dec: declination(L, 0), dist: SUN_DISTANCE_KM };
  }

  function moon(d) {
    const L = RAD * (218.316 + 13.176396 * d); // mean longitude
    const M = RAD * (134.963 + 13.064993 * d); // mean anomaly
    const F = RAD * (93.272 + 13.22935 * d); // mean distance from ascending node
    const l = L + RAD * 6.289 * Math.sin(M);
    const b = RAD * 5.128 * Math.sin(F);
    return { ra: rightAscension(l, b), dec: declination(l, b), dist: 385001 - 20905 * Math.cos(M) };
  }

  /**
   * fraction:  0 (new) .. 1 (full), how much of the disc is lit
   * phase:     0 new, 0.25 first quarter, 0.5 full, 0.75 last quarter
   * limbAngle: direction of the lit side, radians east of celestial north
   */
  function illumination(date) {
    const d = daysSinceJ2000(date);
    const s = sun(d);
    const m = moon(d);
    const elongation = Math.acos(
      Math.sin(s.dec) * Math.sin(m.dec) + Math.cos(s.dec) * Math.cos(m.dec) * Math.cos(s.ra - m.ra));
    const inc = Math.atan2(s.dist * Math.sin(elongation), m.dist - s.dist * Math.cos(elongation));
    const limbAngle = Math.atan2(
      Math.cos(s.dec) * Math.sin(s.ra - m.ra),
      Math.sin(s.dec) * Math.cos(m.dec) - Math.cos(s.dec) * Math.sin(m.dec) * Math.cos(s.ra - m.ra));
    return {
      fraction: (1 + Math.cos(inc)) / 2,
      phase: 0.5 + (0.5 * inc * (limbAngle < 0 ? -1 : 1)) / Math.PI,
      limbAngle,
    };
  }

  /** Rotation of the sky around the Moon as seen from (lat, lng), radians. */
  function parallacticAngle(date, lat, lng) {
    const d = daysSinceJ2000(date);
    const m = moon(d);
    const siderealTime = RAD * (280.16 + 360.9856235 * d) + RAD * lng;
    const H = siderealTime - m.ra; // hour angle
    const phi = RAD * lat;
    return Math.atan2(Math.sin(H), Math.tan(phi) * Math.cos(m.dec) - Math.sin(m.dec) * Math.cos(H));
  }

  function phaseName(phase) {
    const names = ['New Moon', 'Waxing Crescent', 'First Quarter', 'Waxing Gibbous',
                   'Full Moon', 'Waning Gibbous', 'Last Quarter', 'Waning Crescent'];
    // quarters and new/full get a narrow band; crescents and gibbous fill the rest
    const edges = [0.02, 0.235, 0.265, 0.485, 0.515, 0.735, 0.765, 0.98];
    const i = edges.findIndex((e) => phase < e);
    return i === -1 ? names[0] : names[i];
  }

  root.MoonPhase = { illumination, parallacticAngle, phaseName };
})(typeof window !== 'undefined' ? window : globalThis);
