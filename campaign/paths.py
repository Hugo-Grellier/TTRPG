"""Private local state lives outside the source checkout."""

import os
from pathlib import Path


def data_dir():
    override = os.environ.get("TTRPG_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "ttrpg"
