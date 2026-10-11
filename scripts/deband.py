"""Remove 8-bit contour banding from smooth gradients.

Denoising strips the fine noise that was dithering the gradients, so they fall
back onto visible one-level steps that read as moire. Smooth only differences of
a couple of levels in float (never edges), then requantise with random TPDF
dither. Do not switch to ordered dither (e.g. ffmpeg gradfun): its regular grid
aliases into moire again when the image is scaled down.
"""

import argparse

import cv2
import numpy as np
from PIL import Image


def deband(rgb: np.ndarray, range_sigma: float = 2.5, passes: int = 2, seed: int = 0) -> np.ndarray:
    f = rgb.astype(np.float32)
    for _ in range(passes):
        f = cv2.bilateralFilter(f, 17, range_sigma, 8)
    rng = np.random.default_rng(seed)
    dither = rng.random(f.shape, dtype=np.float32) - rng.random(f.shape, dtype=np.float32)
    return np.clip(np.round(f + dither), 0, 255).astype(np.uint8)


def deband_file(src: str, dst: str, range_sigma: float = 2.5) -> None:
    im = Image.open(src)
    alpha = im.getchannel("A") if im.mode == "RGBA" else None
    out = Image.fromarray(deband(np.asarray(im.convert("RGB")), range_sigma))
    if alpha is not None:
        out.putalpha(alpha)
    out.save(dst)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--range", type=float, default=2.5, help="largest step (levels) treated as banding")
    a = p.parse_args()
    deband_file(a.src, a.dst, a.range)
