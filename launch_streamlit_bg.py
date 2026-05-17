from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".deps"))

from streamlit.web import cli as stcli  # noqa: E402


if __name__ == "__main__":
    sys.argv = [
        "streamlit",
        "run",
        str(ROOT / "app.py"),
        "--server.headless",
        "true",
        "--global.developmentMode",
        "false",
    ]
    raise SystemExit(stcli.main())
