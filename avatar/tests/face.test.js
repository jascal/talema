// Run with: node --test avatar/tests/
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Face = require('../public/face.js');

const near = (actual, expected, eps = 1e-9) =>
  assert.ok(Math.abs(actual - expected) < eps, `${actual} is not within ${eps} of ${expected}`);

// A "patch" here is just a number, so blending it is arithmetic we can check by hand.
function composite(photo, patches, weights, order) {
  let out = photo;
  for (const [name, alpha] of Face.layerAlphas(weights, order)) out = out * (1 - alpha) + patches[name] * alpha;
  return out;
}

test('layered blending equals the weighted sum of the images', () => {
  const patches = { a: 20, b: 40, c: 100 };
  const cases = [{ a: 0.2, b: 0.3 }, { a: 0.5 }, { b: 1 }, { a: 0.1, b: 0.1, c: 0.1 }, {}];
  for (const weights of cases) {
    const photo = 10;
    const sum = Object.values(weights).reduce((s, w) => s + w, 0);
    const expected = photo * (1 - sum) + Object.entries(weights).reduce((s, [k, w]) => s + w * patches[k], 0);
    near(composite(photo, patches, weights, ['a', 'b', 'c']), expected);
    // and the drawing order does not change the result
    near(composite(photo, patches, weights, ['c', 'b', 'a']), expected);
  }
});

test('weights that add to more than one are normalised, leaving nothing of the photo', () => {
  const patches = { a: 20, b: 40 };
  near(composite(10, patches, { a: 1, b: 1 }, ['a', 'b']), 30);
});

test('layers that would be invisible are skipped', () => {
  assert.deepEqual(Face.layerAlphas({ a: 0.001, b: 0 }, ['a', 'b']), []);
});

test('the mouth follows the cue under the playhead and rests outside every cue', () => {
  const cues = [
    { start: 0.0, end: 0.1, shape: 'open' },
    { start: 0.1, end: 0.2, shape: 'wide' },
    { start: 0.3, end: 0.4, shape: 'round' },
  ];
  assert.deepEqual(Face.mouthTarget(cues, 0.03), { open: 1 });
  assert.deepEqual(Face.mouthTarget(cues, 0.15), { wide: 1 });
  assert.deepEqual(Face.mouthTarget(cues, 0.25), { rest: 1 });
  assert.deepEqual(Face.mouthTarget(cues, 5), { rest: 1 });
  assert.deepEqual(Face.mouthTarget([], 0), { rest: 1 });
});

test('a vowel prepares the next vowel near the boundary, at most halfway', () => {
  const cues = [{ start: 0, end: 0.1, shape: 'open' }, { start: 0.1, end: 0.2, shape: 'wide' }];
  const target = Face.mouthTarget(cues, 0.0999);
  near(target.open + target.wide, 1);
  assert.ok(target.wide > 0 && target.wide <= 0.5);
  assert.deepEqual(Face.mouthTarget(cues, 0.05), { open: 1 });
});

test('a lip seal is never blended into its neighbours', () => {
  const cues = [{ start: 0, end: 0.1, shape: 'open' }, { start: 0.1, end: 0.2, shape: 'closed' },
    { start: 0.2, end: 0.3, shape: 'wide' }];
  assert.deepEqual(Face.mouthTarget(cues, 0.0999), { open: 1 });
  assert.deepEqual(Face.mouthTarget(cues, 0.15), { closed: 1 });
  assert.deepEqual(Face.mouthTarget(cues, 0.1999), { closed: 1 });
});

test('a shape with no patch falls back to the resting mouth', () => {
  assert.deepEqual(Face.mouthTarget([{ start: 0, end: 1, shape: 'mystery' }], 0.5), { rest: 1 });
});

test('finding a cue works across a long utterance', () => {
  const cues = Array.from({ length: 500 }, (_, i) => ({ start: i * 0.08, end: i * 0.08 + 0.08, shape: 'small' }));
  for (const i of [0, 1, 249, 250, 498, 499]) assert.equal(Face.findCue(cues, i * 0.08 + 0.04), i);
  assert.equal(Face.findCue(cues, 500 * 0.08 + 1), -1);
});

test('the mouth weights stay a set of weights that sum to one', () => {
  const weights = { rest: 1 };
  for (let i = 0; i < 200; i++) Face.stepMouth(weights, i % 40 < 20 ? { open: 1 } : { closed: 0.7, wide: 0.3 }, 1 / 60);
  near(Object.values(weights).reduce((s, w) => s + w, 0), 1);
  for (const w of Object.values(weights)) assert.ok(w >= 0 && w <= 1 + 1e-9);
});

test('a lip seal closes faster than a vowel opens', () => {
  const closing = { open: 1 }, opening = { rest: 1 };
  Face.stepMouth(closing, { closed: 1 }, 1 / 60);
  Face.stepMouth(opening, { open: 1 }, 1 / 60);
  assert.ok(closing.closed > opening.open);
});

test('blinks are between open and shut, start open, and recur', () => {
  const seeded = (() => { let s = 7; return () => ((s = (s * 16807) % 2147483647) / 2147483647); })();
  const closed = Face.createBlinker(seeded);
  assert.equal(closed(0), 0);
  let peak = 0, blinks = 0, was = 0;
  for (let t = 0; t < 60; t += 1 / 60) {
    const c = closed(t);
    assert.ok(c >= 0 && c <= 1, `closedness ${c} out of range at ${t}`);
    peak = Math.max(peak, c);
    if (c > 0.5 && was <= 0.5) blinks += 1;
    was = c;
  }
  assert.ok(peak > 0.9, 'a blink should nearly shut the eye');
  assert.ok(blinks >= 10 && blinks <= 40, `expected a blink every few seconds, got ${blinks} in a minute`);
});

test('the eyes: open shows the photo, shut shows the blink, and the upward look fades under it', () => {
  const open = Face.eyeWeights(0, 1);
  assert.equal(open.blink, 0);
  assert.equal(open.gaze_up, 1);
  const shut = Face.eyeWeights(1, 1);
  near(shut.blink, 1);
  assert.equal(shut.gaze_up, 0);
  for (const closed of [0, 0.2, 0.5, 0.8, 1]) {
    const w = Face.eyeWeights(closed, 0.6);
    assert.ok(Object.values(w).reduce((s, v) => s + v, 0) <= 1 + 1e-9);
  }
});

test('the only eye patches are the ones the renderer draws: no idle glance exists to flash', () => {
  assert.deepEqual(Object.keys(Face.eyeWeights(0.5, 1)).sort(), ['blink', 'gaze_up', 'lids']);
  for (const [name, pose] of Object.entries(Face.POSES)) {
    assert.equal('glance' in pose, false, `${name} should not schedule glances`);
  }
});

test('a look change is a short, monotonic ramp that lands exactly and never overshoots', () => {
  const ramp = Face.createRamp(Face.GAZE_MOVE);
  assert.equal(ramp(0, 10), 0);
  let previous = 0;
  for (let i = 0; i <= 8; i++) {                     // 0 .. 133 ms at 60 fps, the move starting at t = 10
    const v = ramp(1, 10 + i / 60);
    assert.ok(v >= previous && v <= 1, `step ${i}: ${v}`);
    previous = v;
  }
  assert.equal(previous, 1, 'landed by 133 ms');
});

test('only a few frames of a gaze move show both looks at once', () => {
  const ramp = Face.createRamp(Face.GAZE_MOVE);
  ramp(0, 0);
  const frames = Array.from({ length: 10 }, (_, i) => ramp(1, i / 60));   // starts at the first call
  const both = frames.filter(v => v > 0.1 && v < 0.9).length;
  assert.ok(both >= 2 && both <= 5, `${both} of ${frames.length} frames were mid-move: ${frames.map(v => v.toFixed(2))}`);
  assert.ok(Face.GAZE_MOVE < Face.BROW_MOVE && Face.GAZE_MOVE <= 0.15, 'the eyes move faster than the brows, and quickly');
});

test('a ramp does not depend on the frame rate', () => {
  const at = fps => {
    const r = Face.createRamp(0.2);
    r(0, 0); r(1, 0);
    for (let f = 1; f < 0.1 * fps; f++) r(1, f / fps);
    return r(1, 0.1);                                // sampled at exactly 100 ms whatever the rate
  };
  near(at(30), 0.5, 1e-9);
  near(at(60), 0.5, 1e-9);
  near(at(144), 0.5, 1e-9);
});

test('retargeting a ramp mid-move continues from where it got to', () => {
  const ramp = Face.createRamp(0.2);
  ramp(0, 0);
  ramp(1, 0);                                        // start moving at t = 0
  const mid = ramp(1, 0.1);                          // half-way
  near(mid, 0.5, 1e-9);
  near(ramp(0, 0.1), mid, 1e-9);                     // reverse at once: no jump
  assert.ok(ramp(0, 0.15) < mid, 'and then heads back');
  assert.equal(ramp(0, 5), 0);
});

test('moods pick their brows and unknown moods are warm', () => {
  const curious = Face.browTarget('curious');
  assert.ok(curious.right > curious.left + 4, 'curious lifts one brow above the other');
  const thoughtful = Face.browTarget('thoughtful');
  assert.ok(thoughtful.left < 0 && thoughtful.right < 0 && thoughtful.inward > 0, 'thoughtful lowers and draws in');
  const encouraging = Face.browTarget('encouraging');
  assert.ok(encouraging.left > 0 && encouraging.left === encouraging.right, 'encouraging lifts both alike');
  assert.deepEqual(Face.browTarget('no-such-mood'), Face.browTarget('warm'));
  assert.deepEqual(Face.browTarget('warm'), { left: 0, right: 0, inward: 0 });
  assert.equal(Face.moodOf('encouraging').rest, 'smile');
});

test('every brow move is a few pixels, never a large or an implausible one', () => {
  for (const [mood, { brow }] of Object.entries(Face.MOODS)) {
    assert.deepEqual(Object.keys(brow).sort(), [...Face.BROW_KEYS].sort(), mood);
    for (const [key, px] of Object.entries(brow)) {
      assert.ok(Number.isFinite(px) && Math.abs(px) <= 10, `${mood}.${key} = ${px}px is exaggerated`);
    }
  }
});

test('the brows are not photo patches: nothing dissolves, so no second brow can show', () => {
  const shipped = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'public', 'portrait', 'portrait.json'), 'utf8'));
  assert.equal(Object.keys(shipped.patches).some(name => name.startsWith('brows')), false);
  assert.equal(Object.values(shipped.patches).some(p => p.region === 'brows'), false);
});

test('the brows do not move with speech: a steady expression, not a flash on every syllable', () => {
  for (const mood of Object.keys(Face.MOODS)) {
    assert.deepEqual(Face.browTarget(mood, 0), Face.browTarget(mood, 1), mood);
    assert.equal(Face.browTarget.length, 1, 'browTarget takes only the mood');
  }
});

test('a mouth held on one cue settles on it without overshooting or oscillating', () => {
  const weights = { rest: 1 };
  let previous = 0;
  for (let i = 0; i < 120; i++) {
    Face.stepMouth(weights, { open: 1 }, 1 / 60);
    assert.ok(weights.open >= previous - 1e-12, 'the mouth must only move toward its target');
    assert.ok(weights.open <= 1 + 1e-9);
    previous = weights.open;
  }
  assert.ok(weights.open > 0.99);
});

test('a 75 ms cue leaves the mouth on its shape, not still mid-way from the last one', () => {
  const weights = { rest: 1 };
  for (let i = 0; i < 5; i++) Face.stepMouth(weights, { open: 1 }, 1 / 60);   // 83 ms, the length of a cue
  assert.equal(weights.open, 1);
});

test('a shape that has been left is gone completely, with no faint remnant', () => {
  const weights = { rest: 1 };
  for (let i = 0; i < 10; i++) Face.stepMouth(weights, { round: 1 }, 1 / 60);
  assert.equal(weights.round, 1);
  const frames = Math.ceil(Face.MOUTH_MOVE * 60) + 1;
  for (let i = 0; i < frames; i++) Face.stepMouth(weights, { wide: 1 }, 1 / 60);
  assert.equal(weights.round, 0, 'the previous mouth must not linger after MOUTH_MOVE');
  assert.equal(weights.wide, 1);
});

test('through fast speech no more than two mouths overlap, and never a third at any visible strength', () => {
  const shapes = ['open', 'wide', 'round', 'small', 'teeth', 'closed'];
  for (const cueLength of [0.075, 0.09]) {
    const cues = Array.from({ length: 60 }, (_, i) => ({ start: i * cueLength, end: (i + 1) * cueLength, shape: shapes[(i * 5) % 6] }));
    const weights = { rest: 1 };
    let widest = 0;
    for (let f = 0; f < 60 * 60 * cueLength; f++) {
      Face.stepMouth(weights, { ...Face.mouthTarget(cues, f / 60) }, 1 / 60);
      widest = Math.max(widest, Object.values(weights).filter(w => w > 0.02).length);
    }
    assert.ok(widest <= 3, `${widest} mouths were visible at once at ${cueLength * 1000} ms per cue`);
  }
});

test('with a cue longer than a mouth move, only the previous and current shapes are ever visible', () => {
  const shapes = ['open', 'wide', 'round', 'small'];
  const cues = Array.from({ length: 40 }, (_, i) => ({ start: i * 0.09, end: (i + 1) * 0.09, shape: shapes[i % 4] }));
  const weights = { rest: 1 };
  for (let f = 0; f < 40 * 0.09 * 60; f++) {
    Face.stepMouth(weights, { ...Face.mouthTarget(cues, f / 60) }, 1 / 60);
    // coarticulation can add the upcoming shape briefly, so up to three are possible, but the shape before
    // the previous one must be gone
    const t = f / 60, i = Math.floor(t / 0.09);
    if (i >= 2) assert.ok(weights[shapes[(i - 2) % 4]] < 0.02, `${shapes[(i - 2) % 4]} lingered at ${t.toFixed(3)}s`);
  }
});

test('speech energy is normalised to the utterance and is zero when there is no speech', () => {
  assert.equal(Face.buildEnergy([])(0.5), 0);
  const cues = Array.from({ length: 30 }, (_, i) => ({ start: i * 0.09, end: i * 0.09 + 0.09, shape: i % 5 ? 'open' : 'rest' }));
  const at = Face.buildEnergy(cues);
  const values = Array.from({ length: 100 }, (_, i) => at(i * 0.03));
  assert.ok(Math.max(...values) <= 1 && Math.max(...values) > 0.99);
  assert.ok(Math.min(...values) >= 0);
});

test('ten seconds of frames through every state and mood never produce a non-finite or out-of-range weight', () => {
  const shapes = ['closed', 'round', 'wide', 'open', 'teeth', 'small', 'rest'];
  const cues = Array.from({ length: 130 }, (_, i) => ({ start: i * 0.075, end: (i + 1) * 0.075, shape: shapes[(i * 5) % 7] }));
  const closedness = Face.createBlinker();
  const mouth = { rest: 1 }, brows = { left: 0, right: 0, inward: 0 };
  const gazeRamp = Face.createRamp(Face.GAZE_MOVE), browRamps = Object.fromEntries(Face.BROW_KEYS.map(k => [k, Face.createRamp(Face.BROW_MOVE)]));
  const finite = (weights, label) => {
    for (const [k, v] of Object.entries(weights)) assert.ok(Number.isFinite(v) && v >= -1e-9 && v <= 1 + 1e-9, `${label}.${k} = ${v}`);
  };
  const moods = [...Object.keys(Face.MOODS), 'nonsense', undefined];
  const states = [...Object.keys(Face.POSES), 'nonsense'];
  for (let frame = 0; frame < 600; frame++) {
    const t = frame / 60, mood = moods[Math.floor(t / 1.5) % moods.length], state = states[Math.floor(t / 2) % states.length];
    const target = { ...Face.mouthTarget(cues, t) };
    const rest = Face.moodOf(mood).rest;
    if (rest !== 'rest' && target.rest) { target[rest] = target.rest; delete target.rest; }
    Face.stepMouth(mouth, target, 1 / 60);
    const gazeUp = gazeRamp(Face.poseOf(state).gazeUp, t);
    const want = Face.browTarget(mood);
    for (const k of Face.BROW_KEYS) {
      brows[k] = browRamps[k](want[k], t);
      assert.ok(Number.isFinite(brows[k]) && Math.abs(brows[k]) <= 10, `brows.${k} = ${brows[k]}`);
    }
    const eyes = Face.eyeWeights(closedness(t), gazeUp);
    finite(mouth, 'mouth'); finite(eyes, 'eyes');
    for (const [weights, order] of [[mouth, ['closed', 'round', 'wide', 'open', 'teeth', 'small', 'smile']],
      [eyes, ['gaze_up', 'lids', 'blink']]]) {
      for (const [, alpha] of Face.layerAlphas(weights, order)) assert.ok(Number.isFinite(alpha) && alpha > 0 && alpha <= 1 + 1e-9);
    }
  }
});

// ── the assets the code depends on ───────────────────────────────────────────────────────────
const portrait = path.join(__dirname, '..', 'public', 'portrait');
const manifest = JSON.parse(fs.readFileSync(path.join(portrait, 'portrait.json'), 'utf8'));

test('every patch the renderer can ask for exists in the portrait manifest', () => {
  const wanted = [...Face.MOUTH_SHAPES, 'smile', 'lids', 'blink', 'gaze_up'];
  for (const name of wanted) assert.ok(manifest.patches[name], `no patch for ${name}`);
  assert.deepEqual(Object.keys(manifest.patches).sort(), [...wanted].sort(), 'a patch is shipped that nothing draws');
  for (const [name, p] of Object.entries(manifest.patches)) {
    assert.ok(fs.existsSync(path.join(portrait, p.file)), `${name}: ${p.file} is missing`);
    assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= manifest.width && p.y + p.h <= manifest.height, `${name} leaves the photo`);
  }
  assert.ok(fs.existsSync(path.join(portrait, manifest.base)));
});

test('every mouth shape the text-to-speech emits has a patch (or is the resting mouth)', () => {
  const source = fs.readFileSync(path.join(__dirname, '..', 'tts.py'), 'utf8');
  const expression = source.match(/shape = \(([\s\S]*?)\)\n\s+cues\.append/);
  assert.ok(expression, 'could not find the shape expression in tts.py');
  // The names follow "(" or "else"; the quoted phoneme sets follow "in".
  const emitted = new Set([...('(' + expression[1]).matchAll(/(?:\(|else)\s*'(\w+)'/g)].map(m => m[1]));
  assert.ok(emitted.size >= 6, `parsed too few shapes from tts.py: ${[...emitted]}`);
  for (const shape of emitted) {
    if (shape === 'rest') continue;
    assert.ok(Face.MOUTH_SHAPES.includes(shape), `tts.py emits "${shape}", which has no mouth patch`);
  }
  for (const shape of Face.MOUTH_SHAPES) assert.ok(emitted.has(shape), `"${shape}" has a patch but tts.py never emits it`);
});
