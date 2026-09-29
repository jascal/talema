// Luma is a photograph. This composites it in the browser: the phoneme cue under the playhead
// picks a mouth patch, blinks and a look upward swap eye patches, and the tutor's mood moves the brows.
// The patches were edited from the same photo (tools/portrait.py), so they share its lighting and
// skin texture and dissolve into it. The head and shoulders move on a shared warp, so a tilt or a
// breath carries every patch with it. What to show and how much lives in face.js.
(() => {
const canvas = document.querySelector('#character');
const player = document.querySelector('#localAudio');
const stateLabel = document.querySelector('#characterState');
const Face = window.TalemaFace;
const PORTRAIT = '/portrait/';

let cues = [], mood = 'warm', state = 'idle', energyAt = () => 0;
window.character = {
  load(next, emotion) {
    cues = next || [];
    mood = emotion || 'warm';
    energyAt = Face.buildEnergy(cues);
  },
  state(next) {
    state = next || 'idle';
    stateLabel.textContent = state;
    stateLabel.dataset.state = state;
  }
};

// The neck, where the head pivots, and the rows over which the head's motion fades into the
// shoulders, so the jersey stays planted while the head turns.
const PIVOT = [768, 930];
const HEAD_FADE = [800, 1010];
// The mesh reaches this far past the photo (its edge pixels are repeated), so a tilt never
// uncovers the canvas.
const MARGIN = 120;
const COLS = 48, ROWS = 64;

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

const gl = canvas.getContext('webgl2', { alpha: false, antialias: false });
if (!gl) {
  // Without WebGL2 she is still herself, just not moving.
  const flat = canvas.getContext('2d');
  const image = new Image();
  image.onload = () => { if (flat) flat.drawImage(image, 0, 0, canvas.width, canvas.height); };
  image.src = PORTRAIT + 'base.webp';
  return;
}

const VERTEX = `#version 300 es
in vec2 a_grid;
uniform vec4 u_rect;      // where this layer's mesh sits, in portrait pixels
uniform vec4 u_texRect;   // the portrait pixels the texture covers: origin and size
uniform vec2 u_size;      // portrait size
uniform vec2 u_pivot;
uniform vec2 u_fade;      // rows over which the head's motion falls to zero
uniform vec3 u_head;      // dx, dy, tilt in radians
uniform float u_lift;     // breath, in pixels
out vec2 v_uv;
out vec2 v_pos;           // where this point is in the portrait, before the head moves
void main() {
  vec2 p = u_rect.xy + a_grid * u_rect.zw;
  v_uv = (p - u_texRect.xy) / u_texRect.zw;
  v_pos = p;
  float head = 1.0 - smoothstep(u_fade.x, u_fade.y, p.y);
  float a = u_head.z * head;
  vec2 d = p - u_pivot;
  p = u_pivot + vec2(cos(a) * d.x - sin(a) * d.y, sin(a) * d.x + cos(a) * d.y) + u_head.xy * head;
  p.y -= u_lift * (1.0 - 0.45 * head);
  gl_Position = vec4(p.x / u_size.x * 2.0 - 1.0, 1.0 - p.y / u_size.y * 2.0, 0.0, 1.0);
}`;

// The brows move by warping the photo, not by fading in another one: a dissolve between two brows
// shows both while it lasts, and a patch that misses part of the original leaves it showing. Here
// each pixel near a brow is simply read from a few pixels away, so the brow and the skin above it
// shift together and there is only ever one brow. Below a brow the pull fades out faster, so the
// eyelid stays where it is.
const FRAGMENT = `#version 300 es
precision highp float;
uniform sampler2D u_tex;
uniform float u_alpha;
uniform vec4 u_texRect;
uniform vec4 u_brow;      // where the left brow's, then the right brow's, content moves to: dx, dy, dx, dy
in vec2 v_uv;
in vec2 v_pos;
out vec4 o;
// How far a point moves with a brow comes from a map measured from the photo (tools/portrait.py):
// 1 over the brow and the skin above it, so the brow moves as one piece, and 0 on the lashes below.
// Red is the left brow's, green the right's. A formula would not do: the right brow's arch droops to
// the lashes at its outer end, and anything that ignores that drags a few lashes up with it.
uniform sampler2D u_browMap;
uniform vec4 u_browRect;  // where the map sits in the portrait
void main() {
  vec2 pulls = texture(u_browMap, (v_pos - u_browRect.xy) / u_browRect.zw).rg;
  vec2 shift = u_brow.xy * pulls.r + u_brow.zw * pulls.g;
  o = texture(u_tex, v_uv - shift / u_texRect.zw) * u_alpha;   // patches are uploaded premultiplied
}`;

let manifest = null, program = null, uniforms = {}, textures = {}, indexCount = 0, ready = false;

function compile(type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
  return shader;
}

function buildMesh() {
  const grid = new Float32Array((COLS + 1) * (ROWS + 1) * 2);
  let n = 0;
  for (let y = 0; y <= ROWS; y++) for (let x = 0; x <= COLS; x++) { grid[n++] = x / COLS; grid[n++] = y / ROWS; }
  const indices = new Uint16Array(COLS * ROWS * 6);
  n = 0;
  for (let y = 0; y < ROWS; y++) for (let x = 0; x < COLS; x++) {
    const a = y * (COLS + 1) + x, b = a + 1, c = a + COLS + 1, d = c + 1;
    indices.set([a, b, c, b, d, c], n);
    n += 6;
  }
  indexCount = indices.length;
  gl.bindVertexArray(gl.createVertexArray());
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, grid, gl.STATIC_DRAW);
  const at = gl.getAttribLocation(program, 'a_grid');
  gl.enableVertexAttribArray(at);
  gl.vertexAttribPointer(at, 2, gl.FLOAT, false, 0, 0);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);
}

async function loadTexture(file, premultiply, mipmap = true) {
  const image = new Image();
  image.src = PORTRAIT + file;
  await image.decode();
  const texture = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, premultiply);
  gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, image);
  // Mipmaps, so the 1536px photo is filtered down to the stage's size instead of shimmering. (Not the
  // brow map: it is read at full size, and averaging it would only blur it.)
  if (mipmap) gl.generateMipmap(gl.TEXTURE_2D);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, mipmap ? gl.LINEAR_MIPMAP_LINEAR : gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  return texture;
}

async function init() {
  ready = false;
  program = gl.createProgram();
  gl.attachShader(program, compile(gl.VERTEX_SHADER, VERTEX));
  gl.attachShader(program, compile(gl.FRAGMENT_SHADER, FRAGMENT));
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
  gl.useProgram(program);
  uniforms = {};
  for (const name of ['rect', 'texRect', 'size', 'pivot', 'fade', 'head', 'lift', 'tex', 'alpha', 'brow', 'browMap', 'browRect']) {
    uniforms[name] = gl.getUniformLocation(program, 'u_' + name);
  }
  buildMesh();
  manifest = manifest || await (await fetch(PORTRAIT + 'portrait.json')).json();
  const entries = Object.entries(manifest.patches);
  const loaded = await Promise.all([
    loadTexture(manifest.base, false),
    ...entries.map(([, patch]) => loadTexture(patch.file, true)),
  ]);
  textures = { base: loaded[0] };
  entries.forEach(([name], i) => { textures[name] = loaded[i + 1]; });
  // The brow map lives on its own texture unit, so binding photo and patches on unit 0 never disturbs it.
  const map = manifest.browMap;
  const browMap = await loadTexture(map.file, false, false);
  gl.activeTexture(gl.TEXTURE1);
  gl.bindTexture(gl.TEXTURE_2D, browMap);
  gl.activeTexture(gl.TEXTURE0);
  gl.uniform1i(uniforms.tex, 0);
  gl.uniform1i(uniforms.browMap, 1);
  gl.uniform4f(uniforms.browRect, map.x, map.y, map.w, map.h);
  gl.uniform2f(uniforms.size, manifest.width, manifest.height);
  gl.uniform2f(uniforms.pivot, PIVOT[0], PIVOT[1]);
  gl.uniform2f(uniforms.fade, HEAD_FADE[0], HEAD_FADE[1]);
  ready = true;
}

// Size the drawing buffer to the stage: one texel per device pixel up to the photo's own size.
function fit() {
  const wide = Math.min(manifest.width, Math.max(320, Math.round(canvas.clientWidth * (window.devicePixelRatio || 1))));
  const high = Math.round(wide * manifest.height / manifest.width);
  if (canvas.width !== wide || canvas.height !== high) {
    canvas.width = wide;
    canvas.height = high;
  }
  gl.viewport(0, 0, wide, high);
}

// Draw a texture on a mesh at `rect`. `texRect` is the part of the portrait the texture covers; it
// differs from `rect` only for the photo, whose mesh reaches past its edge.
function layer(name, rect, alpha, texRect = rect) {
  const texture = textures[name];
  if (!texture) return;
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.uniform4f(uniforms.rect, ...rect);
  gl.uniform4f(uniforms.texRect, ...texRect);
  gl.uniform1f(uniforms.alpha, alpha);
  gl.drawElements(gl.TRIANGLES, indexCount, gl.UNSIGNED_SHORT, 0);
}

function drawRegion(weights, order) {
  for (const [name, alpha] of Face.layerAlphas(weights, order)) {
    const patch = manifest.patches[name];
    if (patch) layer(name, [patch.x, patch.y, patch.w, patch.h], alpha);
  }
}

// ── animation state ──────────────────────────────────────────────────────────────────────────
const mouth = { rest: 1 };
const brows = { left: 0, right: 0, inward: 0 };
const gazeRamp = Face.createRamp(Face.GAZE_MOVE);
const browRamps = Object.fromEntries(Face.BROW_KEYS.map(key => [key, Face.createRamp(Face.BROW_MOVE)]));
const head = { x: 0, y: 0, rot: 0 };
let energy = 0, last = 0;
const closedness = Face.createBlinker();

const EYE_ORDER = ['gaze_up', 'lids', 'blink'];
const MOUTH_ORDER = [...Face.MOUTH_SHAPES, 'smile'];

function frame(ms) {
  requestAnimationFrame(frame);
  if (!ready) return;
  const t = ms / 1000;
  const dt = last ? Math.min(0.05, t - last) : 1 / 60;
  last = t;
  const speaking = !player.paused && !player.ended;
  const now = speaking ? player.currentTime : -1;
  const calm = reduceMotion.matches ? 0.35 : 1;

  // Mouth: the cue's shape while speaking; between words and when silent, the mood's resting smile.
  const target = speaking ? { ...Face.mouthTarget(cues, now) } : { rest: 1 };
  const resting = Face.moodOf(mood).rest;
  if (resting !== 'rest' && target.rest) {
    target[resting] = target.rest;
    delete target.rest;
  }
  Face.stepMouth(mouth, target, dt);

  energy = Face.approach(energy, speaking ? energyAt(now) : 0, speaking ? 14 : 9, dt);

  // Head: settle toward the state's pose, then add idle sway, breath and a nod that follows speech.
  const want = Face.poseOf(state);
  head.x = Face.approach(head.x, want.x * calm, 5.5, dt);
  head.y = Face.approach(head.y, want.y * calm, 5.5, dt);
  head.rot = Face.approach(head.rot, want.rot * calm, 5.5, dt);
  const breath = Math.sin(t * 1.15) * 2.4 * calm;
  const bob = Math.sin(t * 7.4) * energy * 2.4 * calm;
  const sway = Math.sin(t * 0.62) * 2.2 * calm;
  const tilt = (Math.sin(t * 0.83) * 0.0035 + Math.sin(t * 0.31 + 2) * 0.002 + Math.sin(t * 3.3) * energy * 0.003) * calm;

  // Eyes: look up while thinking, and blink throughout. Nothing else: an idle glance read as a tic.
  const closed = closedness(t);
  const eyes = Face.eyeWeights(closed, gazeRamp(want.gazeUp, t));

  // Brows hold the mood's expression, eased in and out. They do not move with speech or drop for a
  // blink; they are a warp of the photo, so a blink and a brow can never conflict.
  const wantBrows = Face.browTarget(mood);
  for (const key of Face.BROW_KEYS) brows[key] = browRamps[key](wantBrows[key], t);

  fit();
  gl.uniform3f(uniforms.head, head.x + sway * 0.5, head.y + breath * 0.55 + bob, head.rot + tilt);
  gl.uniform1f(uniforms.lift, breath);
  // Content moves up by the lift and inward toward the nose: right for the left brow, left for the right.
  gl.uniform4f(uniforms.brow, brows.inward, -brows.left, -brows.inward, -brows.right);
  gl.disable(gl.BLEND);
  layer('base', [-MARGIN, -MARGIN, manifest.width + 2 * MARGIN, manifest.height + 2 * MARGIN], 1,
    [0, 0, manifest.width, manifest.height]);
  gl.uniform4f(uniforms.brow, 0, 0, 0, 0);          // patches are not part of the brow warp
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  drawRegion(eyes, EYE_ORDER);
  drawRegion(mouth, MOUTH_ORDER);
}

canvas.addEventListener('webglcontextlost', event => { event.preventDefault(); ready = false; });
canvas.addEventListener('webglcontextrestored', () => { init().catch(console.error); });
init().then(() => { fit(); requestAnimationFrame(frame); }).catch(error => console.error('Luma could not load her portrait:', error));
})();
