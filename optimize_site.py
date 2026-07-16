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

UNIFORM_FRAME_CSS = """
  .uniform-shot {
    position: relative; aspect-ratio: 9 / 16; display: flex;
    align-items: center; justify-content: center; isolation: isolate;
    background: var(--cream-alt); overflow: hidden;
  }
  .uniform-shot::before {
    content: ""; position: absolute; inset: -24px; z-index: 0;
    background: var(--shot-bg) center / cover no-repeat;
    filter: blur(18px); transform: scale(1.08); opacity: 0.45;
  }
  .uniform-shot::after {
    content: ""; position: absolute; inset: 0; z-index: 1;
    background: rgba(20, 27, 43, 0.24);
  }
  .uniform-shot > * { position: relative; z-index: 2; }
  .image-stage { position: relative; max-width: 100%; max-height: 100%; }
  .image-stage.fit-height { height: 100%; width: auto; }
  .image-stage.fit-width { width: 100%; height: auto; }
  .step .shot .uniform-shot .image-stage > img {
    width: 100%; height: 100%; object-fit: contain;
  }
  .uniform-shot .tap-marker, .uniform-shot .tap-tag { z-index: 3; }
  .icon-shot::before, .icon-shot::after { display: none; }
  .icon-shot .app-icon-card {
    width: 100%; height: 100%; padding: 30px 18px; background: var(--cream-alt);
  }
""".rstrip()


def find_matching_div(html: str, opening_start: int) -> tuple[int, int]:
    opening_end = html.index(">", opening_start) + 1
    depth = 1
    for match in re.finditer(r"<div\b|</div>", html[opening_end:]):
        token_start = opening_end + match.start()
        if match.group() == "<div":
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return token_start, token_start + len("</div>")
    raise ValueError("Unclosed frame div")


def wrap_step_frame(
    html: str,
    asset_name: str,
    width: int,
    height: int,
    *,
    icon: bool = False,
) -> str:
    image_position = html.index(f'src="assets/{asset_name}"')
    frame_start = html.rfind('<div class="frame">', 0, image_position)
    if frame_start < 0:
        raise ValueError(f"Could not find frame for {asset_name}")

    frame_open_end = html.index(">", frame_start) + 1
    frame_close_start, frame_close_end = find_matching_div(html, frame_start)
    inner = html[frame_open_end:frame_close_start]

    if icon:
        opening = '<div class="frame uniform-shot icon-shot">'
        wrapped_inner = inner
    else:
        fit_class = "fit-height" if width / height <= 9 / 16 else "fit-width"
        opening = (
            '<div class="frame uniform-shot" '
            f'style="--shot-bg: url(\'assets/{asset_name}\');">'
        )
        wrapped_inner = (
            f'<div class="image-stage {fit_class}" '
            f'style="aspect-ratio: {width} / {height};">'
            f"{inner}</div>"
        )

    return (
        html[:frame_start]
        + opening
        + wrapped_inner
        + "</div>"
        + html[frame_close_end:]
    )


def optimize(source_html: Path) -> None:
    html = source_html.read_text(encoding="utf-8")
    html = html.replace(
        ".step .shot .frame img { width: 100%; display: block; }",
        ".step .shot .frame img { width: 100%; height: auto; display: block; }",
    )
    frame_image_rule = (
        ".step .shot .frame img { width: 100%; height: auto; display: block; }"
    )
    html = html.replace(
        frame_image_rule,
        frame_image_rule + "\n" + UNIFORM_FRAME_CSS,
    )

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
    asset_dimensions: dict[str, tuple[int, int]] = {}
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
        asset_dimensions[asset_name] = (width, height)
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
            f' style="aspect-ratio: {width} / {height};" {load_attributes}>'
        )
        replacements[tag] = new_tag

    for old_tag, new_tag in replacements.items():
        html = html.replace(old_tag, new_tag, 1)

    for asset_name in ASSET_NAMES[1:]:
        width, height = asset_dimensions[asset_name]
        html = wrap_step_frame(
            html,
            asset_name,
            width,
            height,
            icon=asset_name == "08-ima-app-icon.webp",
        )

    TARGET_HTML.write_text(html, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: optimize_site.py <embedded-html-source>")
    optimize(Path(sys.argv[1]).resolve())
