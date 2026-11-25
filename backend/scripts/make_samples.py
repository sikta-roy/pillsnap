"""Write sample test photos to ../sample_images (synthetic, never seen in training).

    python scripts/make_samples.py
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.synth import _font, load_catalogue, render_pill  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "sample_images"
CASES = [
    ("dolo-650", "dolo-650_front.jpg", {}),
    ("pan-40", "pan-40_front.jpg", {}),
    ("allegra-120", "allegra-120_front.jpg", {}),
    ("mox-500", "mox-500_capsule.jpg", {}),
    ("voveran-50", "voveran-50_front.jpg", {}),
    ("metolar-50", "metolar-50_front.jpg", {}),
    ("glycomet-500", "glycomet-500_front.jpg", {}),
    ("amlong-5", "white-round_no-imprint_LOW-CONFIDENCE.jpg", {"imprint": ""}),
]


def pack_photo(path: Path):
    """A simple blister-strip label: brand, salt and strength printed on foil."""
    img = Image.new("RGB", (900, 520), (205, 208, 212))
    d = ImageDraw.Draw(img)
    for y in range(0, 520, 6):
        d.line([0, y, 900, y], fill=(198 + (y % 12), 201, 206))
    d.rounded_rectangle([40, 40, 860, 480], 30, outline=(150, 150, 155), width=3)
    d.text((80, 90), "Pan 40", font=_font(110), fill=(200, 30, 40))
    d.text((80, 230), "PANTOPRAZOLE GASTRO-RESISTANT", font=_font(38), fill=(40, 40, 60))
    d.text((80, 285), "TABLETS IP 40 mg", font=_font(38), fill=(40, 40, 60))
    d.text((80, 380), "Alkem  |  EXP 08/2027", font=_font(32), fill=(60, 60, 80))
    img.save(path, quality=92)


def main():
    OUT.mkdir(exist_ok=True)
    cat = {p["pill_id"]: p for p in load_catalogue()}
    rng = np.random.default_rng(2026)
    for pid, name, override in CASES:
        img, _ = render_pill({**cat[pid], **override}, rng, 640)
        img.save(OUT / name, quality=92)
    pack_photo(OUT / "pan-40_strip_for-scan-pack.jpg")
    print("wrote", len(CASES) + 1, "images to", OUT)


if __name__ == "__main__":
    main()
