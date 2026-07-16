import base64
import io
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent
TARGET_HTML = ROOT / "index.html"
ASSET_DIR = ROOT / "assets"
ASSET_NAMES = [
    "01-join-qr.png",
    "02-first-join.webp",
    "03-content-overview.webp",
    "04-wechat-search.webp",
    "05-mini-program-dropdown.webp",
    "06-mini-program-shared-library.webp",
    "07-content-list.webp",
    "08-ima-app-icon.webp",
    "09-app-library-tab.webp",
    "10-app-shared-library.webp",
]


def optimize(source_html: Path) -> None:
    html = source_html.read_text(encoding="utf-8")
    image_tags = re.findall(r"<img\b[^>]*>", html)
    embedded_tags = [tag for tag in image_tags if "data:image/" in tag]
    if len(embedded_tags) != len(ASSET_NAMES):
        raise SystemExit(
            f"Expected {len(ASSET_NAMES)} embedded images, found {len(embedded_tags)}"
        )

    if ASSET_DIR.exists():
        shutil.rmtree(ASSET_DIR)
    ASSET_DIR.mkdir()

    replacements: dict[str, str] = {}
    for index, (tag, asset_name) in enumerate(zip(embedded_tags, ASSET_NAMES)):
        match = re.search(
            r'src="data:image/([^;]+);base64,([^"]+)"',
            tag,
        )
        if not match:
            raise SystemExit(f"Could not parse image tag {index + 1}")

        mime, payload = match.groups()
        raw = base64.b64decode(payload)
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")

        if image.width > 720:
            height = round(image.height * 720 / image.width)
            image = image.resize((720, height), Image.Resampling.LANCZOS)

        output_path = ASSET_DIR / asset_name
        if index == 0:
            output_path.write_bytes(raw)
        else:
            image.save(output_path, "WEBP", quality=84, method=6)

        width, height = image.size
        source = f"assets/{asset_name}"
        new_tag = re.sub(
            r'src="data:image/[^;]+;base64,[^"]+"',
            f'src="{source}"',
            tag,
        )
        load_attributes = (
            'loading="eager" decoding="async" fetchpriority="high"'
            if index == 0
            else 'loading="lazy" decoding="async"'
        )
        new_tag = new_tag[:-1] + (
            f' width="{width}" height="{height}" {load_attributes}>'
        )
        replacements[tag] = new_tag

    for old_tag, new_tag in replacements.items():
        html = html.replace(old_tag, new_tag, 1)

    TARGET_HTML.write_text(html, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: optimize_site.py <embedded-html-source>")
    optimize(Path(sys.argv[1]).resolve())
