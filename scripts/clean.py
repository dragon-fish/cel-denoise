"""waifu2x denoise (scale 1) followed by deband.

    uv run scripts/clean.py IMAGE [IMAGE ...] [--out DIR] [--noise 3]
"""

import argparse
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from deband import deband_file

ROOT = Path(__file__).resolve().parent.parent
W2X_DIR = ROOT / "bin" / "waifu2x"
W2X_EXE = W2X_DIR / ("waifu2x-ncnn-vulkan.exe" if platform.system() == "Windows" else "waifu2x-ncnn-vulkan")


def waifu2x(src: Path, dst: Path, noise: int) -> None:
    cmd = [str(W2X_EXE), "-i", str(src), "-o", str(dst), "-s", "1", "-n", str(noise), "-m", str(W2X_DIR / "models-cunet")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not dst.exists():
        raise RuntimeError(f"waifu2x failed on {src}:\n{r.stderr.strip()}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("images", nargs="+", type=Path)
    p.add_argument("--out", type=Path, default=ROOT / "out")
    # 1 and 2 barely touch this noise: those levels target JPEG artefacts
    p.add_argument("--noise", type=int, default=3, choices=[0, 1, 2, 3])
    p.add_argument("--no-deband", action="store_true")
    a = p.parse_args()

    if not W2X_EXE.exists():
        sys.exit("waifu2x missing: run `uv run scripts/setup_waifu2x.py` first")
    a.out.mkdir(parents=True, exist_ok=True)

    for src in a.images:
        dst = a.out / f"{src.stem}_clean.png"
        if a.no_deband:
            waifu2x(src, dst, a.noise)
        else:
            with tempfile.TemporaryDirectory() as tmp:
                mid = Path(tmp) / "w2x.png"
                waifu2x(src, mid, a.noise)
                deband_file(str(mid), str(dst))
        print(dst)


if __name__ == "__main__":
    main()
