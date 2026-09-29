"""Build Luma's photographic portrait assets.

The avatar is one photograph plus small edited patches of it (mouth shapes, blinks, gaze,
brows). ``character.js`` composites them in the browser to the phoneme cues, so nothing here
runs at serve time and the browser never calls an image API.

Two stages, so the paid one is only ever run deliberately:

    python avatar/tools/portrait.py base  --raw RAW           # generate candidate base portraits
    python avatar/tools/portrait.py edit  --raw RAW [names]   # edit RAW/base.png into each variant
    python avatar/tools/portrait.py build --raw RAW           # local only: composite -> public/portrait/

``RAW`` holds the full-frame generations (about 3 MB each) and is not committed; the encoded
assets in ``avatar/public/portrait/`` are. Choose the base by copying ``RAW/base_N.png`` to
``RAW/base.png``. Every edit is a masked edit of that one image, so the person, lighting and
skin texture stay the same and only the masked region changes.

``generate`` needs OPENAI_API_KEY (read from the repo-root .env). ``build`` needs only Pillow and
numpy:  uv run --no-project --with pillow --with numpy python avatar/tools/portrait.py build --raw RAW
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures as futures
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'avatar' / 'public' / 'portrait'

MODEL = 'gpt-image-2.5-sunburst'   # the docs recommend Sunburst where editing precision matters
SIZE = (1536, 1152)                 # 4:3, like the stage
QUALITY = 'high'

BASE_PROMPT = (
    "Photorealistic portrait photograph of a friendly, approachable young woman (a fictional person), head and "
    "shoulders, shot straight on at eye level with an 85mm lens. She looks directly into the camera with a calm, warm "
    "expression and a soft closed-mouth smile, lips gently together and relaxed. Shoulder-length curly golden-blonde "
    "hair framing her face, warm olive-tan skin with natural texture, visible pores and fine peach fuzz, green-hazel "
    "eyes with natural catchlights, natural eyebrows. She wears a bright pink athletic jersey with two thin white "
    "stripes running down each shoulder, and a fine gold chain necklace with a small round gold pendant set with a "
    "green stone engraved with a leaf. Her head is upright and level, shoulders square to the camera, a perfectly "
    "frontal and symmetrical composition centered in the frame, head about 55% of the frame height with clear space "
    "above her hair. Soft diffused studio key light from the front with a gentle rim light, out-of-focus plain dark "
    "blue-grey seamless backdrop with a subtle teal glow behind her head. Natural, unretouched, sharp focus on the "
    "eyes. No text, no watermark.")

EDIT_PREAMBLE = (
    "This is a photograph of a real woman. Repaint ONLY the masked area; everything outside the mask must stay "
    "identical, including her hair and the edges of her face. Keep the same person, the same skin texture and "
    "pores, the same lighting, colour, focus and photographic grain, at exactly the same position and scale. "
    "The movement is small and natural, as in relaxed ordinary conversation, never theatrical. ")

@dataclass(frozen=True)
class Region:
    """Where a patch may differ from the photo, in portrait pixels.

    ``feather`` is how far the patch's alpha ramps up inside its edge, so a patch dissolves into the photo
    with no seam. The mouth is a polygon that follows the face: it has to reach the smile lines and cheeks,
    which move with the lips, without touching the hair at the jaw, which a rectangle wide enough to do the
    first would."""
    feather: int
    box: tuple[int, int, int, int] | None = None          # left, top, right, bottom
    radius: int = 0                                        # corner radius of a box
    polygon: tuple[tuple[int, int], ...] | None = None

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        if self.polygon:
            xs, ys = [x for x, _ in self.polygon], [y for _, y in self.polygon]
            return min(xs), min(ys), max(xs), max(ys)
        assert self.box
        return self.box


REGIONS = {
    'mouth': Region(feather=26, polygon=(
        (640, 584), (905, 584), (938, 635), (930, 690), (910, 745), (872, 815),
        (700, 815), (665, 752), (648, 700), (630, 650), (628, 610))),
    'eyes':  Region(feather=16, box=(625, 396, 975, 480), radius=30),
}
# The brows have no region: they are a warp of the photo done in the shader (character.js), because a
# patch can only dissolve one brow into another, which shows both while it lasts.

# What the model is also told, per region, beyond the change itself.
REGION_NOTES = {
    'mouth': ("Let the smile lines (the creases running from the nose to the corners of the mouth), the cheeks and "
              "the chin adjust naturally to the new mouth shape: they relax when the mouth is neutral, rounded or "
              "open, and deepen only when she smiles. "),
}

# name -> (region, what the edit changes). Mouth shapes are the ones tts.py emits.
VARIANTS = {
    'closed': ('mouth', "Change only her mouth: the lips pressed gently together in a relaxed, neutral, closed line, not "
                        "smiling and not pursed, as just before saying the letter 'm'. The lips touch along their whole length."),
    'round':  ('mouth', "Change only her mouth: the lips softly rounded, as for a relaxed, quiet 'o' in ordinary "
                        "conversation: a small, gentle rounded opening, the lips only slightly pushed forward. Not pursed, "
                        "not puckered, not a kiss."),
    'wide':   ('mouth', "Change only her mouth: the lips very slightly spread and parted, as for a relaxed, quiet 'ee' in "
                        "ordinary conversation: a hint of the upper teeth and a faint widening at the corners. Not a grin "
                        "and not a broad smile."),
    'open':   ('mouth', "Change only her mouth: a modest, natural opening, as for a relaxed 'ah' in ordinary conversation: "
                        "the jaw lowered only a little, the lips softly parted with the upper teeth visible and a slim "
                        "shadow of the mouth's interior, about a third as open as a wide yawn. Not theatrical, not stretched."),
    'teeth':  ('mouth', "Change only her mouth: the upper front teeth resting very lightly on the inside of the lower lip, as "
                        "when quietly saying the letter 'f'; the lips barely parted and the mouth otherwise relaxed, not smiling widely."),
    'small':  ('mouth', "Change only her mouth: the lips slightly parted with a small gap showing a sliver of the upper "
                        "teeth, the jaw barely lowered, relaxed and neutral, as in the middle of a soft consonant like 'n' or 'd'."),
    'smile':  ('mouth', "Change only her mouth: a slightly wider, warm, encouraging closed-mouth smile, the corners of the "
                        "lips lifted a little higher, lips together, no teeth visible."),
    'blink':  ('eyes',  "Change only her eyes: both eyes gently closed as in a relaxed blink, the upper eyelids lowered onto "
                        "the lower lids with the eyelashes resting downward. Nothing else changes."),
    'lids':   ('eyes',  "Change only her eyes: both eyes half closed, mid-blink, the upper eyelids lowered so they cover "
                        "the top half of each iris. Nothing else changes."),
    'gaze_up':   ('eyes', "Change only her eyes: her gaze drifts slightly up and to the right of the picture, as if she is "
                          "briefly thinking. The irises shift only a little from where they were, toward the upper right; they "
                          "stay largely visible and the eyes stay open. The irises and pupils keep exactly the same green-hazel "
                          "colour and size and the same catchlights. Eyelids, lashes and brows stay the same, and the head "
                          "still faces the camera."),
}


# ── API ──────────────────────────────────────────────────────────────────────────────────────
def _key() -> str:
    if not os.environ.get('OPENAI_API_KEY'):
        env = ROOT / '.env'
        if env.is_file():
            for line in env.read_text().splitlines():
                if '=' in line and not line.lstrip().startswith('#'):
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"\''))
    if not os.environ.get('OPENAI_API_KEY'):
        sys.exit('OPENAI_API_KEY is not set (put it in the repo-root .env).')
    return os.environ['OPENAI_API_KEY']


def _post(url: str, body: bytes, content_type: str, attempts: int = 3) -> dict:
    for attempt in range(attempts):
        request = urllib.request.Request(url, data=body, headers={
            'Authorization': 'Bearer ' + _key(), 'Content-Type': content_type})
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors='replace')[:600]
            if exc.code in (429, 500, 502, 503, 504) and attempt + 1 < attempts:
                time.sleep(8 * (attempt + 1))
                continue
            raise RuntimeError(f'{exc.code}: {detail}') from None
    raise RuntimeError('unreachable')


def _multipart(fields: dict[str, str], files: list[tuple[str, Path]]) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, path in files:
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'
                     f'Content-Type: image/png\r\n\r\n'.encode() + path.read_bytes() + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    return b''.join(parts), f'multipart/form-data; boundary={boundary}'


def _save(result: dict, target: Path, n: int) -> list[Path]:
    saved = []
    for i, item in enumerate(result['data']):
        path = target.with_name(f'{target.stem}_{i}.png') if n > 1 else target
        path.write_bytes(base64.b64decode(item['b64_json']))
        saved.append(path)
    return saved


def shape_mask(name: str, origin: tuple[int, int], size: tuple[int, int]):
    """The region as an 'L' image of ``size`` whose top-left is ``origin`` in the portrait: 255 inside."""
    from PIL import Image, ImageDraw
    region = REGIONS[name]
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    ox, oy = origin
    if region.polygon:
        draw.polygon([(x - ox, y - oy) for x, y in region.polygon], fill=255)
    else:
        left, top, right, bottom = region.bounds
        draw.rounded_rectangle((left - ox, top - oy, right - ox - 1, bottom - oy - 1), radius=region.radius, fill=255)
    return mask


def region_mask(name: str, path: Path) -> None:
    """A mask the size of the portrait: transparent where the model may repaint, opaque elsewhere."""
    from PIL import Image, ImageChops
    mask = Image.new('RGBA', SIZE, (0, 0, 0, 255))
    mask.putalpha(ImageChops.invert(shape_mask(name, (0, 0), SIZE)))
    mask.save(path)


def cmd_base(raw: Path, n: int) -> None:
    body = json.dumps({'model': MODEL, 'prompt': BASE_PROMPT, 'size': f'{SIZE[0]}x{SIZE[1]}',
                       'quality': QUALITY, 'n': n, 'output_format': 'png'}).encode()
    result = _post('https://api.openai.com/v1/images/generations', body, 'application/json')
    for path in _save(result, raw / 'base.png', n):
        print('wrote', path)
    print('Pick one and copy it to', raw / 'base.png')


def edit_one(raw: Path, name: str) -> Path:
    region, change = VARIANTS[name]
    mask = raw / f'mask_{region}.png'
    region_mask(region, mask)
    fields = {'model': MODEL, 'prompt': EDIT_PREAMBLE + REGION_NOTES.get(region, '') + change, 'size': f'{SIZE[0]}x{SIZE[1]}',
              'quality': QUALITY, 'n': '1', 'output_format': 'png'}
    body, content_type = _multipart(fields, [('image[]', raw / 'base.png'), ('mask', mask)])
    result = _post('https://api.openai.com/v1/images/edits', body, content_type)
    (path,) = _save(result, raw / f'{name}.png', 1)
    problem = implausible(raw, name)
    if problem:
        print(f'WARNING {name}: {problem}; regenerate it before building', file=sys.stderr)
    return path


def implausible(raw: Path, name: str) -> str | None:
    """The model sometimes fills the masked area with a flat colour. Catch that before it is built in."""
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return None
    box = REGIONS[VARIANTS[name][0]].bounds
    variant = np.asarray(Image.open(raw / f'{name}.png').convert('L').crop(box), dtype=np.float32)
    photo = np.asarray(Image.open(raw / 'base.png').convert('L').crop(box), dtype=np.float32)
    if variant.std() < 0.35 * photo.std():
        return f'the region is nearly flat (std {variant.std():.0f} against {photo.std():.0f} in the photo)'
    if abs(variant.mean() - photo.mean()) > 0.35 * photo.mean():
        return f'the region is far darker or lighter than the photo ({variant.mean():.0f} against {photo.mean():.0f})'
    return None


def cmd_edit(raw: Path, names: list[str]) -> None:
    if not (raw / 'base.png').is_file():
        sys.exit(f'{raw / "base.png"} is missing; run `base` and pick one first.')
    names = names or list(VARIANTS)
    unknown = [n for n in names if n not in VARIANTS]
    if unknown:
        sys.exit(f'unknown variants {unknown}; choose from {list(VARIANTS)}')
    with futures.ThreadPoolExecutor(4) as pool:
        jobs = {pool.submit(edit_one, raw, name): name for name in names}
        for job in futures.as_completed(jobs):
            try:
                print('wrote', job.result())
            except RuntimeError as exc:
                print('FAILED', jobs[job], exc, file=sys.stderr)


# ── build ────────────────────────────────────────────────────────────────────────────────────
def distance_inside(inside):
    """Distance from each True pixel to the nearest False one (chamfer 3-4, close to Euclidean).

    The frame edge counts as outside, so a region that reaches the edge of its own crop still fades there."""
    import numpy as np
    h, w = inside.shape
    d = np.zeros((h + 2, w + 2), dtype=np.float64)
    d[1:-1, 1:-1] = np.where(inside, 1e9, 0.0)
    rows = d.tolist()
    for y in range(1, h + 1):                           # forward: from the top-left
        row, up = rows[y], rows[y - 1]
        for x in range(1, w + 1):
            if row[x]:
                row[x] = min(row[x], row[x - 1] + 3, up[x] + 3, up[x - 1] + 4, up[x + 1] + 4)
    for y in range(h, 0, -1):                           # backward: from the bottom-right
        row, down = rows[y], rows[y + 1]
        for x in range(w, 0, -1):
            if row[x]:
                row[x] = min(row[x], row[x + 1] + 3, down[x] + 3, down[x - 1] + 4, down[x + 1] + 4)
    return np.asarray(rows)[1:-1, 1:-1] / 3.0


def feather_alpha(name: str):
    """A region's alpha, the size of its bounds: exactly 0 on its rim, exactly 1 from ``feather`` pixels in,
    and a smoothstep between, so a patch dissolves into the photo without a visible edge."""
    import numpy as np
    region = REGIONS[name]
    left, top, right, bottom = region.bounds
    inside = np.asarray(shape_mask(name, (left, top), (right - left, bottom - top))) > 0
    t = np.clip((distance_inside(inside) - 1.0) / region.feather, 0.0, 1.0)
    return np.round(255.0 * t * t * (3.0 - 2.0 * t)).astype(np.uint8)


# ── brows ────────────────────────────────────────────────────────────────────────────────────
# The brows are not patches: character.js moves them by warping the photo, so a second brow can never
# show. What it needs is a map of how far each pixel should move with a brow: 1 on the brow and the
# skin above it, 0 on the lashes just below. An ellipse cannot draw that, because the right brow's arch
# droops down to the lashes at its outer end, so the map is measured from the photo.
BROW_MAP = (600, 320, 1000, 430)          # left, top, right, bottom of the map, in portrait pixels
BROW_FIT = {                              # where to look for each brow, and how dark it is against the skin
    'left':  {'window': (648, 345, 790, 402), 'frac': 0.62, 'outer': 'min'},
    'right': {'window': (830, 366, 990, 414), 'frac': 0.68, 'outer': 'max'},
}
BROW_RAISE = 22      # how far above the brow the skin moves with it
BROW_DROP = 3        # how far below it: enough that its own lower edge moves with the rest
BROW_CUT = 4         # then the pull is gone within at least this many more pixels...
BROW_CUT_MAX = 22    # ...and within as many as the gap to the lashes allows, up to this: the wider the fade,
                     # the less the eyelid skin between brow and lashes is stretched
BROW_TAPER = 26      # the outer tail fades over this many pixels, so it does not drag the lashes it meets


def largest_component(mask):
    """The biggest 4-connected blob of True pixels in ``mask``."""
    import numpy as np
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=bool)
    best: list[tuple[int, int]] = []
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or seen[y, x]:
                continue
            seen[y, x] = True
            stack, blob = [(y, x)], []
            while stack:
                cy, cx = stack.pop()
                blob.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            if len(blob) > len(best):
                best = blob
    out = np.zeros((h, w), dtype=bool)
    for y, x in best:
        out[y, x] = True
    return out


def brow_pull(gray, fit: dict):
    """One brow's pull map (float 0..1, the size of BROW_MAP) from the photo's blurred greyscale."""
    import numpy as np
    from PIL import Image, ImageFilter
    left, top, right, bottom = BROW_MAP
    height, width = bottom - top, right - left
    wl, wt, wr, wb = fit['window']
    region = gray[wt:wb, wl:wr]
    brow = largest_component(region < np.percentile(region, 80) * fit['frac'])
    footprint = np.zeros((height, width), dtype=bool)
    footprint[wt - top:wb - top, wl - left:wr - left] = brow
    # Take in the brow's soft edge, then the skin above it and a sliver below.
    footprint = np.asarray(Image.fromarray(footprint.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(7))) > 0
    reach = footprint.copy()
    for k in range(1, BROW_RAISE + 1):
        reach[:-k] |= footprint[k:]
    for k in range(1, BROW_DROP + 1):
        reach[k:] |= footprint[:-k]
    pull = np.asarray(Image.fromarray(reach.astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(3)),
                      dtype=np.float32) / 255.0
    # Cut it off below the brow's own lower edge, following that edge along its length.
    columns = np.arange(width)
    lowest = np.full(width, np.nan)
    for x in range(width):
        rows = np.nonzero(footprint[:, x])[0]
        if len(rows):
            lowest[x] = rows.max()
    known = ~np.isnan(lowest)
    lowest = np.interp(columns, columns[known], lowest[known])            # past the ends: the nearest edge
    lowest = np.convolve(np.pad(lowest, 10, mode='edge'), np.ones(21) / 21, mode='valid')
    # How far below the brow the first lash is, column by column, so the fade can use all the room there is.
    lash_level = np.percentile(region, 80) * 0.72
    fade = np.full(width, float(BROW_CUT_MAX))
    for x in range(width):
        first = int(lowest[x]) + top + BROW_DROP + 2                       # first row that could be eyelid
        column = gray[first:first + BROW_CUT_MAX + 6, max(left + x - 2, 0):left + x + 3].min(axis=1)
        lashes = np.nonzero(column < lash_level)[0]
        if len(lashes):
            fade[x] = np.clip(lashes[0] - 1, BROW_CUT, BROW_CUT_MAX)
    fade = np.convolve(np.pad(fade, 7, mode='edge'), np.ones(15) / 15, mode='valid')
    below = np.clip((np.arange(height)[:, None] - (lowest[None, :] + BROW_DROP + 1)) / fade[None, :], 0, 1)
    pull *= 1 - below * below * (3 - 2 * below)
    # Fade the outer tail.
    across = np.nonzero(footprint.any(axis=0))[0]
    ahead = (across.max() - columns) if fit['outer'] == 'max' else (columns - across.min())
    taper = np.clip(ahead / BROW_TAPER, 0, 1)
    pull *= (taper * taper * (3 - 2 * taper))[None, :]
    pull[0, :] = pull[-1, :] = pull[:, 0] = pull[:, -1] = 0                   # zero on the rim: clamping is safe
    return np.clip(pull, 0, 1)


def brow_map(base):
    """The two pull maps as one RGBA image: left brow in red, right brow in green, opaque."""
    import numpy as np
    from PIL import Image, ImageFilter
    gray = np.asarray(base.convert('L').filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32)
    left, right = (brow_pull(gray, BROW_FIT[side]) for side in ('left', 'right'))
    rgba = np.zeros(left.shape + (4,), dtype=np.uint8)
    rgba[..., 0] = np.round(left * 255)
    rgba[..., 1] = np.round(right * 255)
    rgba[..., 3] = 255
    return Image.fromarray(rgba, 'RGBA')


def cmd_build(raw: Path) -> None:
    import numpy as np
    from PIL import Image
    OUT.mkdir(parents=True, exist_ok=True)
    base = Image.open(raw / 'base.png').convert('RGB')
    if base.size != SIZE:
        sys.exit(f'base is {base.size}, expected {SIZE}')
    base.save(OUT / 'base.webp', quality=92, method=6)
    manifest = {'width': SIZE[0], 'height': SIZE[1], 'base': 'base.webp', 'patches': {}}
    brow_map(base).save(OUT / 'brows.webp', lossless=True, method=6)    # lossless: it is data, not a picture
    left, top, right, bottom = BROW_MAP
    manifest['browMap'] = {'file': 'brows.webp', 'x': left, 'y': top, 'w': right - left, 'h': bottom - top}
    alphas = {name: feather_alpha(name) for name in REGIONS}
    for name, (region, _) in VARIANTS.items():
        source = raw / f'{name}.png'
        if not source.is_file():
            print('skip (no raw image):', name)
            continue
        left, top, right, bottom = REGIONS[region].bounds
        crop = np.asarray(Image.open(source).convert('RGB').crop((left, top, right, bottom)))
        rgba = np.dstack([crop, alphas[region]])
        file = f'{name}.webp'
        Image.fromarray(rgba, 'RGBA').save(OUT / file, quality=90, alpha_quality=100, method=6)
        manifest['patches'][name] = {'file': file, 'region': region, 'x': left, 'y': top,
                                     'w': right - left, 'h': bottom - top}
    (OUT / 'portrait.json').write_text(json.dumps(manifest, indent=1) + '\n')
    # The folder should hold exactly what the manifest lists: drop patches from variants that no longer exist.
    keep = {manifest['base'], manifest['browMap']['file'], 'portrait.json',
            *(p['file'] for p in manifest['patches'].values())}
    for stale in sorted(p for p in OUT.iterdir() if p.name not in keep):
        print('removing stale', stale.name)
        stale.unlink()
    total = sum(p.stat().st_size for p in OUT.iterdir())
    print(f'built {len(manifest["patches"])} patches into {OUT} ({total / 1024:.0f} KiB)')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('stage', choices=['base', 'edit', 'build'])
    parser.add_argument('names', nargs='*', help='variants to edit (default: all)')
    parser.add_argument('--raw', type=Path, required=True, help='directory for full-frame generations (not committed)')
    parser.add_argument('--n', type=int, default=2, help='candidates for `base`')
    args = parser.parse_args()
    args.raw.mkdir(parents=True, exist_ok=True)
    if args.stage == 'base':
        cmd_base(args.raw, args.n)
    elif args.stage == 'edit':
        cmd_edit(args.raw, args.names)
    else:
        cmd_build(args.raw)


if __name__ == '__main__':
    main()
