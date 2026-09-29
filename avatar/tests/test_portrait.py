"""The portrait assets and the tool that builds them must agree, or the avatar loads a patch that isn't there."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

AVATAR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AVATAR / "tools"))
import portrait  # noqa: E402

PUBLIC = AVATAR / "public" / "portrait"

try:
    import numpy  # noqa: F401
    from PIL import Image
    HAVE_IMAGING = True
except ImportError:  # the project venv carries neither; the tool's build stage documents its own
    HAVE_IMAGING = False


class VariantTable(unittest.TestCase):
    def test_every_variant_names_a_region_that_exists(self):
        for name, (region, _change) in portrait.VARIANTS.items():
            self.assertIn(region, portrait.REGIONS, name)

    def test_regions_sit_inside_the_frame_and_the_feather_fits(self):
        width, height = portrait.SIZE
        for name, region in portrait.REGIONS.items():
            left, top, right, bottom = region.bounds
            self.assertTrue(0 <= left < right <= width and 0 <= top < bottom <= height, name)
            self.assertLess(2 * region.feather, min(right - left, bottom - top), f"{name}: feather swallows the patch")

    def test_the_mouth_region_reaches_the_smile_lines_but_not_the_hair_at_the_jaw(self):
        polygon = portrait.REGIONS["mouth"].polygon
        self.assertIsNotNone(polygon)
        xs = [x for x, _ in polygon]
        self.assertLessEqual(min(xs), 650, "the left smile line runs near x 650-690")
        self.assertGreaterEqual(max(xs), 895, "the right smile line runs near x 860-895")
        # Below the mouth the hair meets the jaw at about x 647 on the left and 930 on the right.
        for x, y in polygon:
            if y >= 745 and x < 770:
                self.assertGreaterEqual(x, 660, f"({x}, {y}) is on the left jaw hair")
            if y >= 740 and x > 770:
                self.assertLessEqual(x, 915, f"({x}, {y}) is on the right jaw hair")

    def test_the_brows_have_no_region(self):
        self.assertNotIn("brows", portrait.REGIONS)
        self.assertFalse([n for n in portrait.VARIANTS if n.startswith("brows")])

    def test_every_edit_is_a_masked_change_to_one_thing(self):
        for name, (_region, change) in portrait.VARIANTS.items():
            self.assertTrue(change.startswith("Change only"), f"{name} should say what it leaves alone")


class CommittedAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((PUBLIC / "portrait.json").read_text())

    def test_the_manifest_lists_exactly_the_variants_the_tool_declares(self):
        self.assertEqual(sorted(self.manifest["patches"]), sorted(portrait.VARIANTS))

    def test_patch_geometry_is_its_region(self):
        for name, patch in self.manifest["patches"].items():
            left, top, right, bottom = portrait.REGIONS[portrait.VARIANTS[name][0]].bounds
            self.assertEqual((patch["x"], patch["y"], patch["w"], patch["h"]), (left, top, right - left, bottom - top), name)
            self.assertEqual(patch["region"], portrait.VARIANTS[name][0], name)

    def test_the_photo_is_the_size_the_tool_and_the_stage_expect(self):
        self.assertEqual((self.manifest["width"], self.manifest["height"]), portrait.SIZE)

    def test_every_file_is_a_webp(self):
        files = ([self.manifest["base"], self.manifest["browMap"]["file"]]
                 + [p["file"] for p in self.manifest["patches"].values()])
        for file in files:
            head = (PUBLIC / file).read_bytes()[:12]
            self.assertEqual((head[:4], head[8:12]), (b"RIFF", b"WEBP"), file)


@unittest.skipUnless(HAVE_IMAGING, "needs Pillow and numpy to decode the images")
class DecodedAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((PUBLIC / "portrait.json").read_text())

    def test_sizes_match(self):
        with Image.open(PUBLIC / self.manifest["base"]) as photo:
            self.assertEqual(photo.size, portrait.SIZE)
        for name, patch in self.manifest["patches"].items():
            with Image.open(PUBLIC / patch["file"]) as image:
                self.assertEqual(image.size, (patch["w"], patch["h"]), name)

    def test_patches_dissolve_into_the_photo_at_their_edge(self):
        for name, patch in self.manifest["patches"].items():
            with Image.open(PUBLIC / patch["file"]) as image:
                alpha = numpy.asarray(image.convert("RGBA"))[:, :, 3]
            rim = numpy.concatenate([alpha[0], alpha[-1], alpha[:, 0], alpha[:, -1]])
            self.assertEqual(int(rim.max()), 0, f"{name}: a patch edge would show as a seam")
            self.assertEqual(int(alpha[alpha.shape[0] // 2, alpha.shape[1] // 2]), 255, f"{name}: centre must be opaque")

    def test_the_brow_map_moves_each_brow_and_the_skin_above_it_but_not_the_lashes_below(self):
        info = self.manifest["browMap"]
        with Image.open(PUBLIC / info["file"]) as image:
            data = numpy.asarray(image.convert("RGBA"))
        self.assertEqual(data.shape[:2], (info["h"], info["w"]))

        def pull(channel, x, y):
            return int(data[y - info["y"], x - info["x"], channel])

        # channel 0 is the left brow (as the viewer sees her), channel 1 the right
        self.assertGreaterEqual(pull(0, 702, 373), 250, "the left brow itself")
        self.assertGreaterEqual(pull(1, 900, 393), 250, "the right brow itself")
        self.assertGreaterEqual(pull(0, 700, 350), 250, "skin above the left brow moves with it")
        self.assertGreaterEqual(pull(1, 900, 365), 250, "skin above the right brow moves with it")
        # The upper lashes sit just below each brow (found by scanning the photo) and must not move with it.
        for x, y in ((680, 410), (700, 424), (720, 420)):
            self.assertLessEqual(pull(0, x, y), 10, f"left lashes at ({x}, {y}) would be dragged up")
        for x, y in ((870, 420), (900, 416), (930, 410), (950, 414)):
            self.assertLessEqual(pull(1, x, y), 10, f"right lashes at ({x}, {y}) would be dragged up")
        # Each brow's map is its own.
        self.assertLessEqual(pull(0, 900, 393), 10)
        self.assertLessEqual(pull(1, 702, 373), 10)
        # Zero on the rim, so clamping the texture is safe.
        for edge in (data[0], data[-1], data[:, 0], data[:, -1]):
            self.assertEqual(int(edge[:, :2].max()), 0)

    def test_the_brow_map_falls_off_gradually_below_the_brow(self):
        """A steep fall-off stretches the eyelid skin between the brow and the lashes; keep it gentle."""
        info = self.manifest["browMap"]
        with Image.open(PUBLIC / info["file"]) as image:
            data = numpy.asarray(image.convert("RGBA"))
        column = data[:, 900 - info["x"], 1].astype(int)          # the middle of the right brow
        steepest = int(numpy.abs(numpy.diff(column)).max())
        self.assertLessEqual(steepest, 40, f"the map drops {steepest}/255 in one pixel, which would visibly stretch the lid")

    def test_feather_ramps_smoothly_from_edge_to_centre(self):
        for region in portrait.REGIONS:
            alpha = portrait.feather_alpha(region)
            row = alpha[alpha.shape[0] // 2].astype(int)
            half = row[: len(row) // 2]
            self.assertTrue((numpy.diff(half) >= 0).all(), f"{region}: alpha should never dip on the way in")
            self.assertLessEqual(int(numpy.diff(half).max()), 64, f"{region}: the ramp is too abrupt to hide a seam")


if __name__ == "__main__":
    unittest.main()
