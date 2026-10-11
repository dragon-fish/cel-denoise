"""Download the waifu2x-ncnn-vulkan release for this OS into bin/.

The binary and its models are not committed; run this once per machine.
Honours https_proxy / http_proxy (urllib reads them).
"""

import io
import platform
import shutil
import stat
import sys
import urllib.request
import zipfile
from pathlib import Path

VERSION = "20250915"
ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "bin" / "waifu2x"

PLATFORMS = {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}


def main() -> None:
    system = platform.system()
    if system not in PLATFORMS:
        sys.exit(f"unsupported OS: {system}")
    name = f"waifu2x-ncnn-vulkan-{VERSION}-{PLATFORMS[system]}"
    url = f"https://github.com/nihui/waifu2x-ncnn-vulkan/releases/download/{VERSION}/{name}.zip"

    print(f"downloading {url}")
    with urllib.request.urlopen(url) as r:
        data = r.read()

    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    prefix = f"{name}/"
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            rel = info.filename.removeprefix(prefix)
            if not rel or info.is_dir():
                continue
            target = DEST / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(info))

    # zipfile drops the executable bit
    exe = DEST / ("waifu2x-ncnn-vulkan.exe" if system == "Windows" else "waifu2x-ncnn-vulkan")
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"installed {exe}")


if __name__ == "__main__":
    main()
