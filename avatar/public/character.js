// A local, real-time character. Mouth cues come from Kokoro's predicted durations.
//
// The face is driven by four signals, all of them real rather than decorative: the
// character's state (idle / speaking / thinking / listening), the emotion the tutor
// returned with the line, the phoneme cue under the playhead, and a speech energy
// envelope derived from how many cues sit near the playhead. Poses are approached with
// exponential smoothing so the character settles into a state instead of snapping to it.
(() => {
const canvas = document.querySelector('#character');
const ctx = canvas.getContext('2d');
const player = document.querySelector('#localAudio');
const stateLabel = document.querySelector('#characterState');

let cues = [], mood = 'warm', state = 'idle';
window.character = {
  load(next, emotion) {
    cues = next || [];
    mood = emotion || 'warm';
    buildEnergyEnvelope();
  },
  state(next) {
    state = next || 'idle';
    stateLabel.textContent = state;
    stateLabel.dataset.state = state;
  }
};

// Half-width, aperture, rounding, upper teeth, tongue, smile. All features share
// this pose, so a rounded vowel cannot leave teeth or a smile outside the lips.
const shapes = {
  rest:   [21, 0, 0, 0, 0, 0.65],
  closed: [20, 0, 0, 0, 0, 0],
  round:  [10, 17, 1, 0.05, 0.1, 0],
  wide:   [25, 9, 0, 0.85, 0.15, 0.12],
  open:   [21, 26, 0.15, 0.55, 0.65, 0],
  teeth:  [21, 4, 0, 1, 0, 0],
  small:  [18, 8, 0.1, 0.35, 0.2, 0],
};
let mouth = [...shapes.rest];

function mouthTarget(time, speaking) {
  if (!speaking) return shapes.rest;
  const index = cues.findIndex(c => time >= c.start && time < c.end);
  if (index < 0) return shapes.rest;
  const cue = cues[index], next = cues[index + 1];
  const current = shapes[cue.shape] || shapes.rest;
  // Prepare the next vowel near a boundary, but preserve the complete lip seal
  // for p/b/m. Pauses also retain a closed, relaxed mouth.
  if (!next || cue.shape === 'closed' || next.shape === 'closed' ||
      cue.shape === 'rest' || next.shape === 'rest' || next.start - cue.end > 0.01) return current;
  const window = Math.min(0.035, (cue.end - cue.start) * 0.3);
  const mix = window > 0 ? Math.max(0, 1 - (cue.end - time) / window) * 0.5 : 0;
  const upcoming = shapes[next.shape] || shapes.rest;
  return current.map((v, i) => v + (upcoming[i] - v) * mix);
}

// ── easing ────────────────────────────────────────────────────────────────────
// Frame-rate independent approach: value += (target - value) * (1 - e^(-rate*dt)).
function approach(current, target, rate, dt) {
  return current + (target - current) * (1 - Math.exp(-rate * dt));
}

// ── poses ─────────────────────────────────────────────────────────────────────
// Each state is a target, not a switch: thinking eases into speaking rather than
// cutting to it. Values are head offset, head tilt, forward lean, brow raise in
// pixels, pupil offset, and eyelid openness.
const POSES = {
  idle:      { x:  0, y:  0, rot:  0.000, brow: 0.0, eyeX: 0, eyeY:  0, lid: 1.00 },
  speaking:  { x:  0, y: -3, rot:  0.004, brow: 1.0, eyeX: 0, eyeY:  0, lid: 1.05 },
  thinking:  { x:  7, y: -7, rot: -0.055, brow: 1.7, eyeX: 2, eyeY: -5, lid: 0.92 },
  listening: { x: -3, y:  3, rot:  0.028, brow: 1.2, eyeX: 0, eyeY:  3, lid: 1.12 },
};
let pose = { ...POSES.idle };

// ── blinking ──────────────────────────────────────────────────────────────────
// A fixed period reads as mechanical, so blinks are scheduled at irregular intervals
// with an occasional double blink, and the lids close and reopen on a real curve.
let nextBlink = 1.4, blinkAt = -1, blinkDone = true, doubleBlink = false;
function scheduleBlink(t) {
  nextBlink = t + 1.6 + Math.random() * 3.4;
  blinkAt = t;
  blinkDone = false;
  doubleBlink = Math.random() < 0.18;
}
function blinkAmount(t) {
  if (blinkDone) {
    if (t >= nextBlink) scheduleBlink(t);
    return 1;
  }
  const since = t - blinkAt;
  const close = 0.11;
  if (since < close) return 1 - Math.sin((since / close) * Math.PI) * 0.94;
  if (doubleBlink && since < close + 0.16) return 1 - Math.sin(((since - close) / 0.1) * Math.PI) * 0.9;
  blinkDone = true;
  return 1;
}

// ── speech energy ─────────────────────────────────────────────────────────────
// How much mouth movement is happening right now, derived from the cues around the
// playhead. This is what makes the brows, blush and background pulse track the actual
// speech instead of running on a fixed animation.
//
// The envelope is built once per utterance and normalised against that utterance's own
// peak. Sampling the cues directly and clamping instead left the signal pinned at 1.0
// for about 90% of a line -- with cues roughly every 90ms and a 90ms window there are
// always two in range -- so every driven feature sat at its maximum and the face looked
// frozen while she spoke. Normalising by the line's own peak restores the range, so the
// brows and blush move with the delivery whatever the speaking rate.
const ENERGY_STEP = 0.04;
const ENERGY_WINDOW = 0.18;
let energyEnvelope = [];
let energyPeak = 1;

function buildEnergyEnvelope() {
  if (!cues.length) { energyEnvelope = []; return; }
  const frames = Math.ceil(cues[cues.length - 1].end / ENERGY_STEP) + 1;
  const raw = new Float32Array(frames);
  for (let i = 0; i < frames; i++) {
    const at = i * ENERGY_STEP;
    let near = 0;
    for (const cue of cues) {
      if (cue.shape === 'rest') continue;
      const distance = Math.max(0, cue.start - at, at - cue.end);
      if (distance < ENERGY_WINDOW) near += 1 - distance / ENERGY_WINDOW;
    }
    raw[i] = near;
  }
  let peak = 0;
  for (const value of raw) peak = Math.max(peak, value);
  energyPeak = peak || 1;
  energyEnvelope = raw;
}

function energyAt(time) {
  if (!energyEnvelope.length) return 0;
  const frame = Math.round(time / ENERGY_STEP);
  const index = frame < 0 ? 0 : Math.min(energyEnvelope.length - 1, frame);
  return energyEnvelope[index] / energyPeak;
}

function ellipse(x, y, rx, ry, color) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.ellipse(x, y, Math.max(0.1, rx), Math.max(0.1, ry), 0, 0, Math.PI * 2);
  ctx.fill();
}

let last = 0;
function draw(ms) {
  const t = ms / 1000;
  const dt = last ? Math.min(0.05, t - last) : 0.016;
  last = t;
  const speaking = !player.paused && !player.ended;
  const now = speaking ? player.currentTime : -1;
  const target = mouthTarget(now, speaking);
  mouth = mouth.map((v, i) => approach(v, target[i], target[1] === 0 ? 48 : 30, dt));
  // A short plosive must reach contact during its cue; easing alone can leave
  // the lips open for the entire p/b/m when it follows a wide vowel.
  if (target === shapes.closed) mouth[1] = 0;
  const energy = speaking ? approach(lookahead.energy, energyAt(now), 14, dt) : approach(lookahead.energy, 0, 9, dt);
  lookahead.energy = energy;
  const openness = Math.max(0, Math.min(1, mouth[1] / 26));

  // Settle toward this state's pose.
  const want = POSES[state] || POSES.idle;
  for (const key of ['x', 'y', 'rot', 'brow', 'eyeX', 'eyeY', 'lid']) {
    pose[key] = approach(pose[key], want[key], 5.5, dt);
  }

  ctx.clearRect(0, 0, 640, 480);
  drawBackdrop(t, energy, state);
  drawAura(t, energy, state);

  // Breathing always, a quicker lift while speaking.
  const breath = Math.sin(t * 1.15) * 1.6;
  const talkBob = Math.sin(t * 7.4) * energy * 1.9;
  const sway = Math.sin(t * 0.62) * 1.1;

  ctx.save();
  ctx.translate(pose.x + sway * 0.5, pose.y + breath + talkBob);
  drawJersey(t, breath, energy);
  drawNecklace(t, energy);
  ctx.restore();

  // The head turns on a pivot at the neck, so the hair and face move as one and the
  // shoulders stay planted.
  ctx.save();
  ctx.translate(320, 336);
  ctx.rotate(pose.rot + Math.sin(t * 0.83) * 0.006);
  ctx.translate(-320, -336 + breath * 0.6 + talkBob * 0.7);
  drawHair(t, energy);
  drawFace(t, energy, openness);
  ctx.restore();

  requestAnimationFrame(draw);
}
const lookahead = { energy: 0 };

// ── backdrop ──────────────────────────────────────────────────────────────────
// A key light behind the head, a cool base, a vignette, and slow drifting motes so the
// stage is not a flat rectangle of colour.
const motes = Array.from({ length: 22 }, (_, i) => ({
  x: (i * 97) % 640,
  y: (i * 53) % 480,
  r: 0.7 + ((i * 7) % 5) * 0.32,
  speed: 5 + ((i * 13) % 11) * 1.5,
  drift: ((i * 29) % 7) - 3,
  phase: i * 0.7,
}));

function drawBackdrop(t, energy) {
  const base = ctx.createLinearGradient(0, 0, 0, 480);
  base.addColorStop(0, '#141d2b');
  base.addColorStop(1, '#0d1119');
  ctx.fillStyle = base;
  ctx.fillRect(0, 0, 640, 480);

  const key = ctx.createRadialGradient(320, 190, 10, 320, 235, 310);
  const warmth = 0.5 + energy * 0.4;
  key.addColorStop(0, `rgba(72, 118, 128, ${0.5 + warmth * 0.24})`);
  key.addColorStop(0.55, 'rgba(38, 62, 82, 0.34)');
  key.addColorStop(1, 'rgba(13, 17, 25, 0)');
  ctx.fillStyle = key;
  ctx.fillRect(0, 0, 640, 480);

  for (const mote of motes) {
    const y = (mote.y - t * mote.speed) % 520;
    const x = mote.x + Math.sin(t * 0.5 + mote.phase) * mote.drift;
    ctx.globalAlpha = 0.1 + 0.12 * (0.5 + 0.5 * Math.sin(t * 0.9 + mote.phase));
    ellipse(x, y < -20 ? y + 520 : y, mote.r, mote.r, '#bfe6ff');
  }
  ctx.globalAlpha = 1;

  const vignette = ctx.createRadialGradient(320, 240, 170, 320, 240, 400);
  vignette.addColorStop(0, 'rgba(0,0,0,0)');
  vignette.addColorStop(1, 'rgba(0,0,0,0.5)');
  ctx.fillStyle = vignette;
  ctx.fillRect(0, 0, 640, 480);
}

// A ring behind the head that swells while she speaks, and a steady soft ring while she
// is thinking, so the state is legible without reading the label.
function drawAura(t, energy, currentState) {
  const active = currentState === 'speaking' || currentState === 'thinking';
  const pulse = currentState === 'speaking' ? energy : (currentState === 'thinking' ? 0.22 + Math.sin(t * 2.1) * 0.1 : 0);
  if (!active || pulse <= 0.01) return;
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  for (let ring = 0; ring < 2; ring++) {
    const phase = (pulse * 1.1 + ring * 0.5) % 1;
    const radius = 132 + phase * 82;
    ctx.globalAlpha = (1 - phase) * 0.3 * pulse + 0.04;
    ctx.strokeStyle = currentState === 'thinking' ? '#a79cff' : '#8ee5c0';
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ctx.ellipse(320, 250, radius, radius * 0.9, 0, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.restore();
}

// ── body ──────────────────────────────────────────────────────────────────────
function drawJersey(t, breath, energy) {
  const lift = breath * 0.5;
  ellipse(320, 481 + lift, 155, 137, '#d93d83');
  ellipse(320, 454 + lift, 118, 101, '#f064a2');
  ctx.strokeStyle = '#fff1f7';
  ctx.lineWidth = 5;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  // Each stripe is the jersey's own shoulder outline moved a fixed distance inward along
  // its normal, so the stripes run down the shoulder at its changing slope and stay
  // parallel, with a pink gap between.
  const [cx, cy, a, b] = [320, 481 + lift, 155, 137];
  for (const side of [-1, 1]) {
    for (const inset of [13, 24]) {
      ctx.beginPath();
      for (let deg = 70; deg >= 24; deg -= 2) {
        const th = deg * Math.PI / 180, nx = Math.cos(th) / a, ny = -Math.sin(th) / b;
        const n = Math.hypot(nx, ny);
        const x = cx + side * (a * Math.cos(th) - inset * nx / n);
        const y = cy - b * Math.sin(th) - inset * ny / n;
        deg === 70 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
  }
  // A small, clean three-stripe mark on the chest.
  ctx.fillStyle = '#fff7fb';
  for (let i = 0; i < 3; i++) {
    ctx.beginPath();
    ctx.moveTo(306 + i * 9, 420);
    ctx.lineTo(312 + i * 9, 410 - i * 3);
    ctx.lineTo(317 + i * 9, 410 - i * 3);
    ctx.lineTo(313 + i * 9, 420);
    ctx.closePath();
    ctx.fill();
  }
  // A tapered neck with a small under-chin shadow, returning to the face's
  // skin tone below the jaw. The curved base meets the shirt without a square edge.
  const skin = ctx.createLinearGradient(0, 330, 0, 375);
  skin.addColorStop(0, '#b68b65');
  skin.addColorStop(0.45, '#cda173');
  skin.addColorStop(1, '#d2a77c');
  ctx.fillStyle = skin;
  ctx.beginPath();
  ctx.moveTo(286, 315);
  ctx.lineTo(354, 315);
  ctx.bezierCurveTo(354, 340, 347, 354, 357, 370);
  ctx.quadraticCurveTo(320, 386, 283, 370);
  ctx.bezierCurveTo(293, 354, 286, 340, 286, 315);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = '#ffd1e2';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.moveTo(283, 371);
  ctx.quadraticCurveTo(320, 388, 357, 371);
  ctx.stroke();
}

// ── hair ──────────────────────────────────────────────────────────────────────
// The locks lag behind the head, so a turn of the head carries through the hair a
// moment later. That lag is most of what makes a drawn character feel alive.
let hairLag = 0, hairSway = 0;
function drawHair(t, energy) {
  hairLag = approach(hairLag, -pose.rot * 34, 6, 1 / 60);
  hairSway = approach(hairSway, pose.x * 0.5, 6, 1 / 60);
  const drift = Math.sin(t * 0.9) * 1.4 + hairSway;

  // The lower hair turns outward behind the jaw and finishes above the collar.
  // Keep the throat clear so these sections read as hair, not straps or a beard.
  ctx.fillStyle = '#b58132';
  ctx.beginPath();
  ctx.moveTo(320, 55);
  ctx.bezierCurveTo(432, 55, 448, 270, 413, 324);
  ctx.bezierCurveTo(407, 342, 384, 359, 365, 351);
  ctx.quadraticCurveTo(383, 333, 369, 308);
  ctx.lineTo(271, 308);
  ctx.quadraticCurveTo(258, 332, 274, 348);
  ctx.bezierCurveTo(254, 356, 232, 339, 226, 321);
  ctx.bezierCurveTo(194, 266, 208, 55, 320, 55);
  ctx.closePath();
  ctx.fill();
  // Curls read as hair rather than as a row of balls when they overlap into one mass,
  // so the lobes are drawn wide and low-contrast with only a soft sheen on each.
  const curls = [
    [241,163,24],[251,120,22],[270,91,23],[297,77,22],[326,73,24],[356,79,23],
    [385,96,22],[405,125,23],[411,163,21],[237,202,20],[403,202,20],
    [258,142,20],[306,101,19],[345,96,20],[381,131,19],[226,182,18],[415,182,18],
    [288,84,17],[364,86,17],
  ];
  for (const [x, y, r] of curls) {
    ellipse(x + drift * 0.25, y, r, r * 0.94, '#e4b449');
    ellipse(x - 3 + drift * 0.25, y - 4, r * 0.46, r * 0.38, '#efc65c');
  }
  for (const side of [-1, 1]) {
    const offset = drift * 0.5 + hairLag;
    const tipY = side === -1 ? 344 : 350;
    ctx.fillStyle = '#d6a03c';
    ctx.beginPath();
    ctx.moveTo(320 + side * 78 + offset, 137);
    ctx.bezierCurveTo(320 + side * 110 + offset, 185,
      320 + side * 103 + offset, 231, 320 + side * 96 + offset, 267);
    ctx.bezierCurveTo(320 + side * 87 + offset, 305,
      320 + side * 96 + offset, 326, 320 + side * 61 + offset, tipY);
    ctx.bezierCurveTo(320 + side * 76 + offset, 323,
      320 + side * 65 + offset, 308, 320 + side * 66 + offset, 283);
    ctx.bezierCurveTo(320 + side * 59 + offset, 250,
      320 + side * 57 + offset, 222, 320 + side * 57 + offset, 205);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = 'rgba(246, 205, 106, 0.65)';
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(320 + side * 86 + offset, 178);
    ctx.bezierCurveTo(320 + side * 94 + offset, 231,
      320 + side * 77 + offset, 280, 320 + side * 82 + offset, 306);
    ctx.quadraticCurveTo(320 + side * 85 + offset, 320,
      320 + side * 73 + offset, tipY - 13);
    ctx.stroke();
  }
  drawEar(216, -1);
  drawEar(424, 1);
  for (const x of [222, 418]) {
    ellipse(x, 255, 3.2, 3.2, '#f5d474');
    ctx.save();
    ctx.translate(x, 265);
    ctx.scale(0.62, 0.62);
    ctx.fillStyle = '#f071a6';
    ctx.strokeStyle = '#ffe0eb';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(0, 10);
    ctx.bezierCurveTo(-5, 6, -13, 1, -12, -5);
    ctx.bezierCurveTo(-11, -13, -2, -13, 0, -7);
    ctx.bezierCurveTo(3, -13, 12, -13, 12, -5);
    ctx.bezierCurveTo(13, 1, 5, 6, 0, 10);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.restore();
  }
}

// Ears sit behind the face; detail stays on the exposed outer half. Mirroring
// local coordinates keeps both folds directed inward toward the cheek.
function drawEar(x, side) {
  ctx.save();
  ctx.translate(x, 230);
  ctx.scale(side, 1);
  const skin = ctx.createLinearGradient(-5, 0, 12, 0);
  skin.addColorStop(0, '#b78560');
  skin.addColorStop(0.65, '#cda173');
  skin.addColorStop(1, '#dbb087');
  ctx.fillStyle = skin;
  ctx.beginPath();
  ctx.moveTo(-5, -16);
  ctx.bezierCurveTo(2, -23, 12, -18, 12, -8);
  ctx.bezierCurveTo(13, 2, 8, 10, 6, 17);
  ctx.bezierCurveTo(4, 23, -4, 23, -6, 16);
  ctx.quadraticCurveTo(-10, 0, -5, -16);
  ctx.closePath();
  ctx.fill();

  // Shallow concha, shaded softly rather than drawn as a dark hole.
  ellipse(2, 1, 4.5, 9, 'rgba(150, 91, 68, 0.24)');
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.strokeStyle = '#e3b992';
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.moveTo(-2, -15);
  ctx.bezierCurveTo(6, -20, 10, -13, 9, -5);
  ctx.quadraticCurveTo(9, 4, 5, 10);
  ctx.stroke();

  // Inner fold forks near the top and curves into the bowl above the lobe.
  ctx.strokeStyle = 'rgba(143, 91, 64, 0.55)';
  ctx.lineWidth = 1.3;
  ctx.beginPath();
  ctx.moveTo(4, -11);
  ctx.quadraticCurveTo(-1, -7, 2, -2);
  ctx.quadraticCurveTo(7, 3, 1, 9);
  ctx.moveTo(2, -2);
  ctx.quadraticCurveTo(0, -6, -3, -7);
  ctx.stroke();
  ellipse(-1, 6, 2.4, 3.8, '#cda173');
  ellipse(0, 16, 3.3, 3.6, 'rgba(233, 185, 148, 0.42)');
  ctx.restore();
}

// ── face ──────────────────────────────────────────────────────────────────────
function drawFace(t, energy, openness) {
  // Face: wider through the jaw with a blunt chin. A narrow taper here read as a long
  // face, which is the one proportion that made her look severe rather than warm.
  ctx.fillStyle = '#cda173';
  ctx.beginPath();
  ctx.moveTo(320, 108);
  ctx.bezierCurveTo(386, 108, 420, 156, 422, 210);
  ctx.bezierCurveTo(425, 258, 408, 296, 380, 320);
  ctx.quadraticCurveTo(352, 338 + openness * 4, 320, 340 + openness * 5);
  ctx.quadraticCurveTo(288, 338 + openness * 4, 260, 320);
  ctx.bezierCurveTo(232, 296, 215, 258, 218, 210);
  ctx.bezierCurveTo(220, 156, 254, 108, 320, 108);
  ctx.closePath();
  ctx.fill();

  // Fringe sweeping across the brow.
  ctx.fillStyle = '#e9b84a';
  ctx.beginPath();
  ctx.moveTo(225, 211);
  ctx.bezierCurveTo(209, 41, 433, 47, 421, 216);
  ctx.bezierCurveTo(387, 194, 376, 125, 360, 123);
  ctx.bezierCurveTo(323, 180, 263, 157, 225, 211);
  ctx.fill();

  drawBlush(energy);
  drawEyes(t, energy);
  drawBrows(t, energy);
  drawNose();
  drawMouth();
}

// Cheeks warm while she speaks and stay warm for a friendly mood. Kept translucent so
// the skin still reads through.
function drawBlush(energy) {
  const warm = mood === 'warm' || mood === 'cheerful' ? 0.08 : 0.03;
  ctx.globalAlpha = 0.1 + warm + energy * 0.2;
  for (const [x, y] of [[266, 270], [374, 270]]) {
    ellipse(x, y, 28, 14, '#dd6b58');
  }
  ctx.globalAlpha = 1;
}

function drawEyes(t, energy) {
  const blink = blinkAmount(t);
  const curious = mood === 'curious';
  const lid = Math.max(0.06, blink * pose.lid);
  for (const [x, side, index] of [[282, -1, 0], [359, 1, 1]]) {
    // Curious lifts the far lid a little, which is the interested look without
    // redrawing the eye.
    const squint = curious && index === 1 ? 1.12 : 1;
    const ry = 10 * lid * squint;
    const gazeX = pose.eyeX + Math.sin(t * 0.35) * 1.4;
    const gazeY = pose.eyeY;
    ellipse(x, 229, 20, ry, '#fff6ea');
    // A wide pupil when she is animated, a calmer one at rest.
    const pupil = 6.6 + energy * 1.4;
    ellipse(x + gazeX, 229 + gazeY, pupil, 8.4 * lid * squint, '#4a6b5c');
    ellipse(x + gazeX, 229 + gazeY, pupil * 0.44, 5.4 * lid * squint, '#1d2f2c');
    // Catchlight. Small, but it is most of the difference between a drawn eye and a
    // living one.
    if (lid > 0.4) {
      ctx.globalAlpha = 0.85;
      ellipse(x + gazeX - 2.4, 226.2 + gazeY, 2.5, 2.5 * lid, '#ffffff');
      ctx.globalAlpha = 0.5;
      ellipse(x + gazeX + 2.6, 232 + gazeY, 1.1, 1.1 * lid, '#d8f2e6');
      ctx.globalAlpha = 1;
    }
    // A soft rim, not a drawn outline: a hard line here reads as spectacle frames.
    ctx.strokeStyle = 'rgba(150,110,74,.5)';
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.ellipse(x, 229, 20, ry, 0, 0, Math.PI * 2);
    ctx.stroke();
    // The lid only appears while blinking, as a skin-toned sweep over the top of the
    // eye, so a closed eye reads as a lid closing rather than an eye shrinking.
    if (lid < 0.94) {
      ctx.fillStyle = '#cda173';
      ctx.beginPath();
      ctx.ellipse(x, 229 - 11, 21, 11 + 10 * lid, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#8a6444';
      ctx.lineWidth = 1.8;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(x - 20, 228);
      ctx.quadraticCurveTo(x, 229 - ry * 0.2, x + 20, 228);
      ctx.stroke();
    }
  }
}

function drawBrows(t, energy) {
  const curious = mood === 'curious';
  const warm = mood === 'cheerful';
  for (const [x, side, index] of [[282, -1, 0], [359, 1, 1]]) {
    // Curious raises one brow and tilts the pair; speech lifts both with the energy.
    const asym = curious && index === 1 ? 5 : 0;
    const y = 205 - pose.brow * 4.5 - energy * 3.4 - asym;
    const arch = (warm ? 7 : 4) + pose.brow * 1.6 + (curious && index === 1 ? 2 : 0);
    const tilt = curious ? (index === 1 ? -4.5 : 1.5) : 0;
    // A brow drawn as a soft tapered stroke rather than a flat bar, so the expression
    // reads as movement instead of a heavier pair of marks.
    ctx.strokeStyle = '#8a5f39';
    ctx.lineWidth = 4.2;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(x - 18, y + 5 + tilt);
    ctx.quadraticCurveTo(x - 2, y - arch, x + 13, y - 1 - tilt);
    ctx.stroke();
    ctx.strokeStyle = 'rgba(138,95,57,.5)';
    ctx.lineWidth = 2.4;
    ctx.beginPath();
    ctx.moveTo(x + 12, y - 1.5 - tilt);
    ctx.quadraticCurveTo(x + 16, y + 1 - tilt, x + 19, y + 4 - tilt);
    ctx.stroke();
  }
}

function drawNose() {
  ctx.strokeStyle = '#9e7856';
  ctx.lineWidth = 3;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(319, 239);
  ctx.lineTo(313, 262);
  ctx.quadraticCurveTo(320, 268, 327, 261);
  ctx.stroke();
}

function drawMouth() {
  const [width, aperture, round, teeth, tongue, smile] = mouth;
  const h = Math.max(0, aperture);
  const corner = -smile * 3;
  const top = -h * 0.36;
  const bottom = h * 0.64;
  ctx.save();
  ctx.translate(320, 293);
  ctx.lineCap = 'round';

  // A single contour owns the lips and the aperture. Rounded vowels use fuller
  // side walls; spread vowels taper to corners. The upper lip has a subtle bow.
  function contour(w, upper, lower) {
    const shoulder = 0.62 + round * 0.3;
    ctx.beginPath();
    ctx.moveTo(-w, corner);
    ctx.bezierCurveTo(-w * shoulder, upper, -w * 0.3, upper - 1, 0, upper + 0.7);
    ctx.bezierCurveTo(w * 0.3, upper - 1, w * shoulder, upper, w, corner);
    ctx.bezierCurveTo(w * shoulder, lower, w * 0.4, lower + 1, 0, lower + 1);
    ctx.bezierCurveTo(-w * 0.4, lower + 1, -w * shoulder, lower, -w, corner);
    ctx.closePath();
  }

  // Lip colour is shaded rather than outlined with a second, unrelated smile.
  const lip = ctx.createLinearGradient(0, top - 4, 0, bottom + 5);
  lip.addColorStop(0, '#984652');
  lip.addColorStop(0.48, '#b76270');
  lip.addColorStop(1, '#d18488');
  contour(width + 2, top - 3, bottom + 3);
  ctx.fillStyle = lip;
  ctx.fill();

  if (h > 0.65) {
    contour(width, top, bottom);
    ctx.fillStyle = '#42242c';
    ctx.fill();
    ctx.save();
    ctx.clip();

    // The tongue sits low in the cavity. Both it and the dental arch are clipped
    // to the actual opening, including during transitions into an O or a closure.
    ctx.globalAlpha = tongue;
    ellipse(0, bottom + 2, width * 0.68, Math.max(2, h * 0.25), '#bd737e');
    ctx.globalAlpha = teeth;
    const toothBottom = top + Math.min(5.5, 2 + h * 0.22);
    const enamel = ctx.createLinearGradient(0, top, 0, toothBottom);
    enamel.addColorStop(0, '#cdbbb0');
    enamel.addColorStop(1, '#fff2dc');
    ctx.fillStyle = enamel;
    ctx.beginPath();
    ctx.moveTo(-width * 0.82, top - 4);
    ctx.lineTo(width * 0.82, top - 4);
    ctx.lineTo(width * 0.78, toothBottom - 1.5);
    ctx.quadraticCurveTo(0, toothBottom + 1.5, -width * 0.78, toothBottom - 1.5);
    ctx.closePath();
    ctx.fill();
    // A restrained central division, avoiding a row of floating white blocks.
    ctx.strokeStyle = 'rgba(117, 88, 80, 0.18)';
    ctx.lineWidth = 0.65;
    ctx.beginPath();
    ctx.moveTo(0, top);
    ctx.lineTo(0, toothBottom);
    ctx.stroke();
    ctx.restore();
  } else {
    ctx.strokeStyle = '#874653';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(-width, corner);
    ctx.quadraticCurveTo(0, 1 + smile * 3, width, corner);
    ctx.stroke();
  }

  // Highlight follows the lower lip, never crosses the cavity or rounded corners.
  ctx.strokeStyle = 'rgba(255, 205, 190, 0.36)';
  ctx.lineWidth = 1.1;
  ctx.beginPath();
  ctx.moveTo(-width * 0.38, bottom + 2.7);
  ctx.quadraticCurveTo(0, bottom + 4.2, width * 0.38, bottom + 2.7);
  ctx.stroke();
  ctx.restore();
}

function drawNecklace(t, energy) {
  // Anchored to the torso/neck transform, so a head tilt cannot pull the chain
  // off the neck. Both strands meet the bail, rather than ending above the pendant.
  const swing = Math.sin(t * 2.1) * energy * 1.5;
  const center = 320 + swing;
  ctx.save();
  ctx.lineCap = 'round';
  function chain(offset = 0) {
    ctx.beginPath();
    ctx.moveTo(291, 351 + offset);
    ctx.bezierCurveTo(290, 364 + offset, 301, 380 + offset, center, 389 + offset);
    ctx.bezierCurveTo(338, 380 + offset, 350, 364 + offset, 349, 351 + offset);
  }
  chain(1);
  ctx.strokeStyle = 'rgba(96, 66, 49, 0.3)';
  ctx.lineWidth = 2.8;
  ctx.stroke();
  const metal = ctx.createLinearGradient(290, 350, 350, 390);
  metal.addColorStop(0, '#b29356');
  metal.addColorStop(0.35, '#ffe5a1');
  metal.addColorStop(0.7, '#d4b56e');
  metal.addColorStop(1, '#f7dc95');
  chain();
  ctx.strokeStyle = metal;
  ctx.lineWidth = 1.8;
  ctx.stroke();

  // Small connecting ring and a gold bezel around the green pendant.
  ctx.strokeStyle = '#eed28c';
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.ellipse(center, 391, 2.3, 3.2, 0, 0, Math.PI * 2);
  ctx.stroke();
  ellipse(center + 0.8, 402, 9.4, 11.3, 'rgba(87, 43, 62, 0.22)');
  ellipse(center, 400, 9, 11, '#ba9655');
  ellipse(center, 399.5, 7.7, 9.5, '#f5d795');
  const stone = ctx.createLinearGradient(center - 6, 391, center + 6, 409);
  stone.addColorStop(0, '#b9f2d6');
  stone.addColorStop(0.45, '#6fc9ab');
  stone.addColorStop(1, '#348f83');
  ellipse(center, 399.5, 6.3, 8, stone);

  // A small engraved leaf on the face: central vein and two pairs of branches.
  ctx.strokeStyle = '#397e6d';
  ctx.lineWidth = 0.85;
  ctx.beginPath();
  ctx.moveTo(center - 1.5, 404.5);
  ctx.quadraticCurveTo(center + 1.5, 400, center + 0.5, 394.5);
  ctx.moveTo(center, 401.5);
  ctx.lineTo(center - 3, 398.5);
  ctx.moveTo(center + 0.7, 399.5);
  ctx.lineTo(center + 3.4, 397);
  ctx.stroke();
  ctx.strokeStyle = 'rgba(238, 255, 238, 0.75)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.ellipse(center, 399.5, 5, 6.8, 0, Math.PI * 1.05, Math.PI * 1.55);
  ctx.stroke();
  ctx.restore();
}

requestAnimationFrame(draw);
})();
