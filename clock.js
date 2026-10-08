// Runs the clock on the moth's disk from the device's own local time.

const NS = 'http://www.w3.org/2000/svg';
const hourHand = document.getElementById('hourHand');
const minuteHand = document.getElementById('minuteHand');
const secondHand = document.getElementById('secondHand');
const clock = document.querySelector('.clock');

// Dots for the hours without numerals.
const dots = document.getElementById('dots');
for (let h = 1; h < 12; h++) {
  if (h % 3 === 0) continue;
  const a = (h / 12) * 2 * Math.PI;
  const dot = document.createElementNS(NS, 'circle');
  dot.setAttribute('cx', (Math.sin(a) * 92).toFixed(2));
  dot.setAttribute('cy', (-Math.cos(a) * 92).toFixed(2));
  dot.setAttribute('r', '3.6');
  dots.appendChild(dot);
}

const turn = (el, deg) => el.setAttribute('transform', `rotate(${deg.toFixed(3)})`);

function tick() {
  const now = new Date();
  const s = now.getSeconds();
  const m = now.getMinutes() + s / 60;
  const h = (now.getHours() % 12) + m / 60;
  turn(secondHand, s * 6);
  turn(minuteHand, m * 6);
  turn(hourHand, h * 30);
  clock.setAttribute('aria-label', `Clock showing ${now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`);
  // land on the next whole second so the second hand ticks in step with the device clock
  setTimeout(tick, 1000 - now.getMilliseconds());
}

tick();
// Timers are throttled in background tabs; catch up straight away when the page is shown again.
document.addEventListener('visibilitychange', () => { if (!document.hidden) tick(); });
