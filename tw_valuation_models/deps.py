from __future__ import annotations

import site
import sys
from pathlib import Path


def bootstrap_local_deps(workspace_root: Path) -> Path:
    deps_root = workspace_root / ".deps"
    if deps_root.exists():
        site.addsitedir(str(deps_root))
        if str(deps_root) not in sys.path:
            sys.path.insert(0, str(deps_root))
    return deps_root
