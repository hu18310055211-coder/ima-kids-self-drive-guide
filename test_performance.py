import re
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
HTML_PATH = ROOT / "index.html"
ASSET_DIR = ROOT / "assets"


class PublicGuidePerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = HTML_PATH.read_text(encoding="utf-8")
        cls.img_tags = re.findall(r"<img\b[^>]*>", cls.html)

    def test_html_is_small_and_does_not_embed_images(self) -> None:
        self.assertLess(HTML_PATH.stat().st_size, 100_000)
        self.assertNotIn("data:image", self.html)

    def test_all_ten_images_are_local_assets(self) -> None:
        self.assertEqual(len(self.img_tags), 10)
        sources = [re.search(r'src="([^"]+)"', tag).group(1) for tag in self.img_tags]
        self.assertTrue(all(source.startswith("assets/") for source in sources))
        self.assertTrue(all((ROOT / source).is_file() for source in sources))

    def test_below_fold_images_are_lazy_and_async(self) -> None:
        self.assertIn('loading="eager"', self.img_tags[0])
        self.assertIn('fetchpriority="high"', self.img_tags[0])
        for tag in self.img_tags[1:]:
            self.assertIn('loading="lazy"', tag)
            self.assertIn('decoding="async"', tag)

    def test_image_assets_fit_mobile_budget(self) -> None:
        assets = sorted(ASSET_DIR.glob("*"))
        self.assertEqual(len(assets), 10)
        self.assertLess(sum(path.stat().st_size for path in assets), 900_000)
        for path in assets:
            self.assertLess(path.stat().st_size, 250_000)
            with Image.open(path) as image:
                self.assertLessEqual(image.width, 720)

    def test_join_link_and_qr_value_are_unchanged(self) -> None:
        share_url = (
            "https://ima.qq.com/wiki/?shareId="
            "5791dde976186ffb37d13837a24fbc02e0492e932dbaf67937b3b3ce83444f4b"
        )
        self.assertIn(f'href="{share_url}"', self.html)
        self.assertIn(f'data-qr-value="{share_url}"', self.html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
