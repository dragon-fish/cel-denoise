"""Measure flat-fill noise and banding; build zoomed comparison boards.

    uv run scripts/analyze.py stats IMAGE [IMAGE ...]
    uv run scripts/analyze.py board --box X,Y,SIZE --out board.png IMAGE [IMAGE ...]

Not named inspect.py: scripts/ is on sys.path and would shadow the stdlib module.
"""

import argparse
import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def load_rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32)


def c2pa(path: Path) -> str:
    raw = path.read_bytes()
    if b"c2pa" not in raw:
        return "none"
    marks = sorted({m.decode() for m in re.findall(rb"c2pa\.watermarked(?:\.unbound|\.bound)?", raw)})
    return "C2PA" + (f" ({', '.join(marks)})" if marks else "")


def flat_fill_masks(rgb: np.ndarray, min_px: int = 5000) -> list[np.ndarray]:
    """Large regions of one colour, eroded away from their outlines; pure black/white excluded."""
    q = (cv2.GaussianBlur(rgb, (0, 0), 2) // 12).astype(np.int32)
    key = q[..., 0] * 10000 + q[..., 1] * 100 + q[..., 2]
    vals, counts = np.unique(key, return_counts=True)
    masks = []
    for v in vals[np.argsort(counts)[::-1][:8]]:
        m = cv2.erode((key == v).astype(np.uint8), np.ones((11, 11), np.uint8)).astype(bool)
        if m.sum() >= min_px and 2 < rgb[m].mean() < 250:
            masks.append(m)
    return masks


def fill_noise(rgb: np.ndarray, masks: list[np.ndarray]) -> float:
    """Std (8-bit levels) of the fine residual inside the flat fills; slow shading drift is excluded."""
    if not masks:
        return float("nan")
    res = rgb - cv2.GaussianBlur(rgb, (0, 0), 1.5)
    return float(np.mean([res[m].std(0).mean() for m in masks]))


def fill_mottle(rgb: np.ndarray, masks: list[np.ndarray]) -> float:
    """Std (8-bit levels) of the 1.5-6 px band inside the flat fills: the blotchy AI texture.

    Kept apart from fill_noise: deband's dither puts single-pixel white noise back into
    fill_noise, which says nothing about this band.
    """
    if not masks:
        return float("nan")
    band = cv2.GaussianBlur(rgb, (0, 0), 1.5) - cv2.GaussianBlur(rgb, (0, 0), 6)
    return float(np.mean([band[m].std(0).mean() for m in masks]))


def banding(rgb: np.ndarray) -> float:
    """Share of equal horizontal neighbours on gentle gradients; rises when gradients collapse into steps."""
    g = rgb[..., 1]
    sm = cv2.GaussianBlur(g, (0, 0), 3)
    slope = np.hypot(cv2.Sobel(sm, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(sm, cv2.CV_32F, 0, 1, ksize=3)) / 8
    m = (slope > 0.05) & (slope < 1.5) & (sm > 4) & (sm < 251)
    eq = np.zeros_like(m)
    eq[:, 1:] = np.round(g[:, 1:]) == np.round(g[:, :-1])
    m[:, 0] = False
    return float(eq[m].mean()) if m.any() else float("nan")


def cmd_stats(paths: list[Path]) -> None:
    for p in paths:
        rgb = load_rgb(p)
        masks = flat_fill_masks(rgb)
        print(f"{p.name}\n  provenance  {c2pa(p)}\n  fill noise  {fill_noise(rgb, masks):.2f} levels"
              f"\n  fill mottle {fill_mottle(rgb, masks):.2f} levels\n  banding     {banding(rgb):.2f}")


def cmd_board(paths: list[Path], box: str, out: Path, zoom: int, gain: float) -> None:
    """Top row: crop at `zoom`x. Bottom row: deviation from an 8px blur, amplified by `gain`."""
    x, y, s = map(int, box.split(","))
    S = s * zoom
    board = Image.new("RGB", ((S + 8) * len(paths) - 8, S * 2 + 8), "white")
    for i, p in enumerate(paths):
        crop = load_rgb(p)[y : y + s, x : x + s]
        g = crop.mean(2)
        dev = np.clip(128 + (g - cv2.GaussianBlur(g, (0, 0), 8)) * gain, 0, 255).astype(np.uint8)
        for row, tile in enumerate([crop.astype(np.uint8), np.stack([dev] * 3, 2)]):
            board.paste(Image.fromarray(tile).resize((S, S), Image.NEAREST), (i * (S + 8), row * (S + 8)))
    board.save(out)
    print(out)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stats")
    s.add_argument("images", nargs="+", type=Path)
    b = sub.add_parser("board")
    b.add_argument("images", nargs="+", type=Path)
    b.add_argument("--box", required=True, help="X,Y,SIZE of the square crop")
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--zoom", type=int, default=4)
    b.add_argument("--gain", type=float, default=4)
    a = p.parse_args()
    if a.cmd == "stats":
        cmd_stats(a.images)
    else:
        cmd_board(a.images, a.box, a.out, a.zoom, a.gain)


if __name__ == "__main__":
    main()
