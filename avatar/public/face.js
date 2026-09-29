// The face's logic, kept free of the DOM and of WebGL so it can be tested in Node.
//
// Luma is one photograph plus small edited patches of it (see tools/portrait.py). Everything
// here answers one question: how much of each patch is visible right now? Every patch belongs to a
// region (mouth, eyes, brows), and the photo itself is that region's neutral state, so each region
// is a set of weights that sum to one.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.TalemaFace = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const clamp01 = v => Math.max(0, Math.min(1, v));

  // Frame-rate independent approach: value += (target - value) * (1 - e^(-rate*dt)).
  function approach(current, target, rate, dt) {
    return current + (target - current) * (1 - Math.exp(-rate * dt));
  }

  // How long the eyes take to move between looks, in seconds.
  const GAZE_MOVE = 0.12;

  // A move between two values, over a fixed time. The eyes change look by dissolving one photo into
  // another, so until the move is over both positions are visible at once. An exponential ease has a
  // long tail and leaves that double image on screen for half a second; a real saccade takes about
  // 80 ms, so the move is a short smoothstep ramp that is over before it can be read as two. (The brows
  // use it too, for a smooth start and stop.) Retargeting mid-move continues from wherever it has got to.
  function createRamp(duration, initial = 0) {
    let from = initial, to = initial, start = 0, value = initial;
    return function at(target, now) {
      if (target !== to) { from = value; to = target; start = now; }
      const p = clamp01((now - start) / duration);
      value = from + (to - from) * p * p * (3 - 2 * p);
      return value;
    };
  }

  // ── compositing ────────────────────────────────────────────────────────────────────────────
  // Layers are drawn one over another, so a set of weights becomes a list of opacities. The photo
  // is the first layer and takes whatever weight the patches leave; patch k is drawn at
  // w_k / (w_photo + w_1 + ... + w_k), which makes the result exactly sum(w_i * image_i).
  function layerAlphas(weights, order) {
    let total = 0;
    for (const name of order) total += Math.max(0, weights[name] || 0);
    const scale = total > 1 ? 1 / total : 1;
    let running = Math.max(0, 1 - total * scale);
    const layers = [];
    for (const name of order) {
      const w = Math.max(0, weights[name] || 0) * scale;
      if (w < 0.002) continue;
      running += w;
      layers.push([name, w / running]);
    }
    return layers;
  }

  // ── mouth ──────────────────────────────────────────────────────────────────────────────────
  // The shapes tts.py emits, plus `rest`, which is the photo's own closed, gently smiling mouth.
  const MOUTH_SHAPES = ['closed', 'round', 'wide', 'open', 'teeth', 'small'];

  function findCue(cues, time) {
    let lo = 0, hi = cues.length - 1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (time < cues[mid].start) hi = mid - 1;
      else if (time >= cues[mid].end) lo = mid + 1;
      else return mid;
    }
    return -1;
  }

  // The mouth the cues ask for at `time`, as weights. Near a boundary the next vowel is prepared,
  // but a p/b/m keeps its complete lip seal and a pause keeps a closed, relaxed mouth.
  function mouthTarget(cues, time) {
    const index = findCue(cues, time);
    if (index < 0) return { rest: 1 };
    const cue = cues[index], next = cues[index + 1];
    const shape = cue.shape === 'rest' || MOUTH_SHAPES.includes(cue.shape) ? cue.shape : 'rest';
    if (!next || cue.shape === 'closed' || next.shape === 'closed' ||
        cue.shape === 'rest' || next.shape === 'rest' || next.start - cue.end > 0.01) return { [shape]: 1 };
    const span = Math.min(0.035, (cue.end - cue.start) * 0.3);
    const mix = span > 0 ? Math.max(0, 1 - (cue.end - time) / span) * 0.5 : 0;
    const upcoming = MOUTH_SHAPES.includes(next.shape) ? next.shape : 'rest';
    if (mix <= 0 || upcoming === shape) return { [shape]: 1 };
    return { [shape]: 1 - mix, [upcoming]: mix };
  }

  // How long a mouth shape takes to give way completely, in seconds. A lip seal is quicker, or a short
  // p/b/m would end before the lips met.
  const MOUTH_MOVE = 0.06, LIP_SEAL_MOVE = 0.04;

  // Move every mouth weight toward its target at a constant speed, and keep them summing to one.
  //
  // The speed is constant, not an exponential ease, on purpose. Easing decays with a long tail, so at
  // a cue every 75 ms the two or three mouths before this one are all still faintly on screen: lips
  // from words ago lingering over the current shape. At a constant speed a shape that has been left
  // is gone, exactly, within MOUTH_MOVE, and with cues longer than that only two shapes ever overlap.
  function stepMouth(weights, target, dt) {
    const step = dt / (target.closed > 0.5 ? LIP_SEAL_MOVE : MOUTH_MOVE);
    let sum = 0;
    for (const key of ['rest', ...MOUTH_SHAPES, 'smile']) {
      const w = weights[key] || 0, goal = target[key] || 0;
      weights[key] = w < goal ? Math.min(goal, w + step) : Math.max(goal, w - step);
      sum += weights[key];
    }
    if (sum > 0) for (const key in weights) weights[key] /= sum;
    return weights;
  }

  // ── eyes ───────────────────────────────────────────────────────────────────────────────────
  // How closed the eyelids are (0 open, 1 shut). Blinks come at irregular intervals with an
  // occasional double, and close faster than they reopen, which is what a real lid does.
  function createBlinker(random = Math.random) {
    let next = 1.4, at = -1, finished = true, double = false;
    const CLOSE = 0.045, OPEN = 0.075, GAP = 0.06;
    function lidCurve(since) {
      if (since < CLOSE) return Math.sin((since / CLOSE) * Math.PI / 2);
      if (since < CLOSE + OPEN) return Math.cos(((since - CLOSE) / OPEN) * Math.PI / 2);
      return 0;
    }
    return function closed(t) {
      if (finished) {
        if (t < next) return 0;
        next = t + 1.6 + random() * 3.4;
        at = t;
        finished = false;
        double = random() < 0.08;
      }
      const since = t - at;
      const length = CLOSE + OPEN;
      if (since < length) return lidCurve(since) * 0.97;
      if (double && since < length + GAP + length) return since < length + GAP ? 0 : lidCurve(since - length - GAP) * 0.9;
      finished = true;
      return 0;
    };
  }

  // Patches for the eyes: open (the photo), half-lidded, shut, and a glance up. A blink takes over
  // from whatever the eyes were doing, so the glance fades out as the lids come down.
  function eyeWeights(closed, gazeUp) {
    const open = 1 - closed;
    const shut = clamp01((closed - 0.25) / 0.5);
    return { lids: closed * (1 - shut), blink: closed * shut, gaze_up: gazeUp * open };
  }

  // ── brows ──────────────────────────────────────────────────────────────────────────────────
  // The brows are not photo patches. Dissolving one photo of a brow into another always shows two brows
  // while it lasts, and under a patch that does not cover the whole original the old brow never goes.
  // Instead the shader moves the brow and the skin above it, a few pixels, in the one photograph
  // (character.js). There is nothing to fade in, so there is nothing to see twice.
  //
  // Each brow moves in portrait pixels: `left` and `right` lift it (negative lowers it), and `inward`
  // draws both toward the nose. "Left" and "right" are as the viewer sees her.
  const BROW_KEYS = ['left', 'right', 'inward'];
  const BROW_MOVE = 0.25;   // seconds for the brows to settle into a new mood

  // The tutor returns one of these moods with each line. `rest` is the mouth patch shown between words.
  const MOODS = {
    warm:        { brow: { left: 0,  right: 0,  inward: 0 }, rest: 'rest'  },
    curious:     { brow: { left: 1,  right: 7,  inward: 0 }, rest: 'rest'  },
    thoughtful:  { brow: { left: -2, right: -2, inward: 3 }, rest: 'rest'  },
    encouraging: { brow: { left: 4,  right: 4,  inward: 0 }, rest: 'smile' },
  };

  function moodOf(name) {
    return MOODS[name] || MOODS.warm;
  }

  // Where the brows want to be: the mood's, held steadily. They used to lift with speech energy, but a
  // brow that moves on every syllable reads as flashing, not as expression.
  function browTarget(mood) {
    return { ...moodOf(mood).brow };
  }

  // ── speech energy ──────────────────────────────────────────────────────────────────────────
  // How much mouth movement is happening around the playhead, built once per utterance and
  // normalised against that utterance's own peak. Sampled and clamped instead, it sat at 1.0 for
  // about 90% of a line and every driven feature looked frozen while she spoke.
  const ENERGY_STEP = 0.04;
  const ENERGY_WINDOW = 0.18;

  function buildEnergy(cues) {
    if (!cues.length) return () => 0;
    const frames = Math.ceil(cues[cues.length - 1].end / ENERGY_STEP) + 1;
    const raw = new Float32Array(frames);
    let peak = 0;
    for (let i = 0; i < frames; i++) {
      const at = i * ENERGY_STEP;
      let near = 0;
      for (const cue of cues) {
        if (cue.shape === 'rest') continue;
        const distance = Math.max(0, cue.start - at, at - cue.end);
        if (distance < ENERGY_WINDOW) near += 1 - distance / ENERGY_WINDOW;
      }
      raw[i] = near;
      if (near > peak) peak = near;
    }
    peak = peak || 1;
    return time => {
      const frame = Math.round(time / ENERGY_STEP);
      return raw[frame < 0 ? 0 : Math.min(frames - 1, frame)] / peak;
    };
  }

  // ── pose ───────────────────────────────────────────────────────────────────────────────────
  // Head offset in portrait pixels (of 1536 x 1152), tilt in radians, and whether the eyes glance up. Each
  // state is a target the head eases toward, so thinking settles into speaking instead of cutting.
  const POSES = {
    idle:      { x:   0, y:  0, rot:  0.000, gazeUp: 0 },
    speaking:  { x:   0, y: -3, rot:  0.002, gazeUp: 0 },
    thinking:  { x:  14, y: -8, rot: -0.028, gazeUp: 1 },
    listening: { x:  -6, y:  6, rot:  0.014, gazeUp: 0 },
  };

  function poseOf(name) {
    return POSES[name] || POSES.idle;
  }

  return {
    approach, clamp01, createRamp, GAZE_MOVE, BROW_MOVE, layerAlphas, MOUTH_SHAPES, MOUTH_MOVE, findCue, mouthTarget, stepMouth,
    createBlinker, eyeWeights, MOODS, BROW_KEYS, moodOf, browTarget, buildEnergy, POSES, poseOf,
  };
});
