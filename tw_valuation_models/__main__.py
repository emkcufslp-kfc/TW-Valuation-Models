from pathlib import Path

from .deps import bootstrap_local_deps


bootstrap_local_deps(Path(__file__).resolve().parents[1])

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
