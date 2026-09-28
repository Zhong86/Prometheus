"""Puts the backend source tree on sys.path so Athena components can reuse app.tools.*.

Langflow loads each component file directly rather than as an installed
package, so ``backend/`` isn't on sys.path by default. ``flows/`` and
``backend/`` are siblings in this repo — that relative layout holds both
under a bare local ``langflow run`` and under the docker-compose service,
which mounts the whole repo into the container (see /flows/README.md).
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_SRC = Path(__file__).resolve().parents[3] / "backend"
if _BACKEND_SRC.is_dir() and str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))
