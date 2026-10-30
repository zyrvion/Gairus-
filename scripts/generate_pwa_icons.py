"""Build public PNGs from the existing typographic G, not a new logo.

Development dependency only: Pillow and a locally installed Noto Sans bold.
Runtime serves committed PNGs and does not import Pillow.
"""

from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont


def main():
    font_path = subprocess.check_output(
        ["fc-match", "-f", "%{file}", "Noto Sans:style=Bold"], text=True
    ).strip()
    destination = Path(__file__).resolve().parents[1] / "static"
    for size in (180, 192, 512):
        image = Image.new("RGB", (size, size), "#111827")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(font_path, round(size * .57))
        bounds = draw.textbbox((0, 0), "G", font=font)
        x = (size - (bounds[2] - bounds[0])) / 2 - bounds[0]
        y = (size - (bounds[3] - bounds[1])) / 2 - bounds[1]
        draw.text((x, y), "G", fill="#ffffff", font=font)
        image.save(destination / f"icon-{size}.png", optimize=True)


if __name__ == "__main__":
    main()
