from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = Path(sys.executable)
LOG_OUT = ROOT / "_tmp_streamlit_bg.out"
LOG_ERR = ROOT / "_tmp_streamlit_bg.err"


def main() -> int:
    env = os.environ.copy()
    deps_path = str(ROOT / ".deps")
    env["PYTHONPATH"] = deps_path if not env.get("PYTHONPATH") else deps_path + os.pathsep + env["PYTHONPATH"]

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    if os.name == "nt":
        command = (
            f'"{PYTHON}" -m streamlit run "{ROOT / "app.py"}" '
            "--server.headless true --global.developmentMode false "
            f'1>>"{LOG_OUT}" 2>>"{LOG_ERR}"'
        )
        subprocess.Popen(
            ["cmd.exe", "/c", command],
            cwd=str(ROOT),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=True,
        )
    else:
        with LOG_OUT.open("ab") as out_handle, LOG_ERR.open("ab") as err_handle:
            subprocess.Popen(
                [
                    str(PYTHON),
                    "-m",
                    "streamlit",
                    "run",
                    str(ROOT / "app.py"),
                    "--server.headless",
                    "true",
                    "--global.developmentMode",
                    "false",
                ],
                cwd=str(ROOT),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=out_handle,
                stderr=err_handle,
                creationflags=creationflags,
                close_fds=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
