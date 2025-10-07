import os
import platform
import sys
from pathlib import Path


def add_env_bin_to_path() -> None:
    env_root = Path(sys.prefix)
    bin_folder = env_root / "Library" / "bin" if platform.system() == "Windows" else env_root / "bin"
    os.environ["PATH"] = str(bin_folder) + ";" + os.environ["PATH"]
