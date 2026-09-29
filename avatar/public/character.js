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

const shapes = {rest:[19,2],closed:[21,1],round:[10,15],wide:[26,8],open:[20,20],teeth:[22,5],small:[16,8]};
let mouth = [19, 2];

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
      const distance = at < cue.start ? cue.start - at : at - cue.end;
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
  const cue = speaking ? cues.find(c => now >= c.start && now < c.end) : null;
  const target = shapes[cue && cue.shape || 'rest'];
  mouth = mouth.map((v, i) => approach(v, target[i], 26, dt));
  const energy = speaking ? approach(lookahead.energy, energyAt(now), 14, dt) : approach(lookahead.energy, 0, 9, dt);
  lookahead.energy = energy;
  const openness = Math.max(0, Math.min(1, (mouth[1] - 8) / 12));

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
  ctx.fillStyle = '#9b774d';
  ctx.fillRect(293, 303, 54, 76);
  ellipse(320, 354, 29, 20, '#9b774d');
}

// ── hair ──────────────────────────────────────────────────────────────────────
// The locks lag behind the head, so a turn of the head carries through the hair a
// moment later. That lag is most of what makes a drawn character feel alive.
let hairLag = 0, hairSway = 0;
function drawHair(t, energy) {
  hairLag = approach(hairLag, -pose.rot * 34, 6, 1 / 60);
  hairSway = approach(hairSway, pose.x * 0.5, 6, 1 / 60);
  const drift = Math.sin(t * 0.9) * 1.4 + hairSway;

  ellipse(320 + drift * 0.2, 225, 108, 170, '#a87328');
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
    ctx.fillStyle = '#c68a30';
    ctx.beginPath();
    ctx.moveTo(320 + side * 78 + drift * 0.2, 137);
    ctx.bezierCurveTo(320 + side * 111 + drift, 187, 320 + side * 99 + drift, 226, 320 + side * 91 + drift, 260);
    ctx.bezierCurveTo(320 + side * 82 + drift, 299, 320 + side * 103 + drift, 332, 320 + side * 87 + drift, 366);
    ctx.bezierCurveTo(320 + side * 81 + drift, 382, 320 + side * 69 + drift, 391, 320 + side * 62 + drift, 393);
    ctx.bezierCurveTo(320 + side * 71 + drift, 367, 320 + side * 59 + drift, 350, 320 + side * 66 + drift, 324);
    ctx.bezierCurveTo(320 + side * 49 + drift, 283, 320 + side * 57 + drift, 243, 320 + side * 57 + drift, 205);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = '#f0c65f';
    ctx.lineWidth = 4;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(320 + side * 86 + drift * 0.5, 178);
    ctx.bezierCurveTo(320 + side * 76 + drift * 0.8, 225, 320 + side * 78 + drift * 0.8, 262, 320 + side * 85 + drift * 0.8, 288);
    ctx.stroke();
    ellipse(320 + side * 64 + drift, 374, 9, 12, '#e5b64d');
  }
  ellipse(216, 230, 12, 20, '#c08e5f');
  ellipse(424, 230, 12, 20, '#c08e5f');
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

// ── face ──────────────────────────────────────────────────────────────────────
function drawFace(t, energy, openness) {
  // Face: wider through the jaw with a blunt chin. A narrow taper here read as a long
  // face, which is the one proportion that made her look severe rather than warm.
  ctx.fillStyle = '#cda173';
  ctx.beginPath();
  ctx.moveTo(320, 108);
  ctx.bezierCurveTo(386, 108, 420, 156, 422, 210);
  ctx.bezierCurveTo(425, 258, 408, 296, 380, 320);
  ctx.quadraticCurveTo(352, 338, 320, 340);
  ctx.quadraticCurveTo(288, 338, 260, 320);
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
  drawMouth(openness);
  drawNecklace(t, energy);
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

function drawMouth(openness) {
  // Soft rose lipstick stays visible at rest and follows each speaking shape.
  function mouthShape(rx, ry, color, spread = 0) {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(320 - rx, 293);
    ctx.bezierCurveTo(320 - rx * 0.72, 291 - ry * 0.32, 320 - rx * 0.32, 292 - ry, 320, 292 - ry);
    ctx.bezierCurveTo(320 + rx * 0.32, 292 - ry, 320 + rx * 0.72, 291 - ry * 0.32, 320 + rx, 293);
    ctx.bezierCurveTo(320 + rx * 0.82, 294 + ry * 0.4, 320 + rx * 0.48, 294 + ry, 320, 294 + ry + spread);
    ctx.bezierCurveTo(320 - rx * 0.48, 294 + ry, 320 - rx * 0.82, 294 + ry * 0.4, 320 - rx, 293);
    ctx.closePath();
    ctx.fill();
  }
  mouthShape(mouth[0] + 3, Math.max(4, mouth[1] + 3), '#b84f70', openness * 3);
  mouthShape(mouth[0], Math.max(1, mouth[1] - 1), '#572638', openness * 2);
  if (mouth[1] > 4) {
    mouthShape(mouth[0] - 3, Math.max(1, mouth[1] - 3), '#402832', openness);
    ctx.fillStyle = '#fff0df';
    ctx.beginPath();
    ctx.moveTo(306, 289);
    ctx.quadraticCurveTo(320, 287, 334, 289);
    ctx.lineTo(333, 292);
    ctx.quadraticCurveTo(320, 290, 307, 292);
    ctx.closePath();
    ctx.fill();
  }
  ctx.strokeStyle = '#e58ba0';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(298, 291);
  ctx.quadraticCurveTo(308, 287, 316, 291);
  ctx.quadraticCurveTo(320, 294, 324, 291);
  ctx.quadraticCurveTo(333, 287, 342, 291);
  ctx.stroke();
  // The lip seam deepens into a smile as the mouth closes. Without it she sits at rest
  // with a flat line for a mouth, which is what made an idle avatar look severe; a
  // speaking shape should flatten back to neutral rather than keep the smile.
  const smile = Math.max(0, 1 - openness * 2.4);
  ctx.strokeStyle = '#8c3852';
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  ctx.moveTo(299, 295 - smile * 6);
  ctx.quadraticCurveTo(320, 304 + smile * 4, 341, 295 - smile * 6);
  ctx.stroke();
  if (smile > 0.45) {
    // A soft dimple at each corner, which is what makes a drawn smile read as one.
    ctx.globalAlpha = (smile - 0.45) * 1.5;
    ctx.strokeStyle = '#b0764c';
    ctx.lineWidth = 1.6;
    for (const x of [299, 341]) {
      ctx.beginPath();
      ctx.moveTo(x, 293 - smile * 5);
      ctx.quadraticCurveTo(x - 4, 288, x - 3, 282);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }
}

function drawNecklace(t, energy) {
  const swing = Math.sin(t * 2.1) * energy * 3;
  ctx.strokeStyle = '#8ee5c0';
  ctx.lineWidth = 3;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(294, 380);
  ctx.quadraticCurveTo(320 + swing, 403, 346, 380);
  ctx.stroke();
  ellipse(320 + swing, 403, 5, 7, '#8ee5c0');
}

requestAnimationFrame(draw);
})();
