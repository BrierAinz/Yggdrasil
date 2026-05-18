import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Make all active Yggdrasil realms and sub-packages importable in tests
# ---------------------------------------------------------------------------
YGGDRASIL_ROOT = Path(__file__).parent.parent.resolve()

# Active realms with installable packages
_ACTIVE_REALMS = ["Asgard", "Vanaheim", "Muspelheim", "Alfheim", "Svartalfheim", "Midgard"]

for realm in _ACTIVE_REALMS:
    realm_path = YGGDRASIL_ROOT / realm
    if realm_path.exists() and str(realm_path) not in sys.path:
        sys.path.insert(0, str(realm_path))

# Sub-packages within realms that need their own sys.path entry
# (e.g. Asgard/lilith-memory -> allows `from lilith_memory.store import ...`)
_SUB_PACKAGES = [
    "Asgard/lilith-api",
    "Asgard/lilith-bridge",
    "Asgard/lilith-cli",
    "Asgard/lilith-core",
    "Asgard/lilith-memory",
    "Asgard/lilith-orchestrator",
    "Asgard/lilith-skills",
    "Asgard/lilith-tools",
    "Alfheim/dashboard",
    "Alfheim/TerminalDashboard",
    "Muspelheim/AutoSub",
    "Muspelheim/ForgeMaster",
    "Vanaheim/bifrost",
    "Vanaheim/vanaheim-framework",
]

for subpkg in _SUB_PACKAGES:
    subpkg_path = YGGDRASIL_ROOT / subpkg
    if subpkg_path.exists() and str(subpkg_path) not in sys.path:
        sys.path.insert(0, str(subpkg_path))


@pytest.fixture
def yggdrasil_root():
    """Return the root path of the Yggdrasil monorepo."""
    return YGGDRASIL_ROOT


@pytest.fixture
def tmp_yggdrasil(tmp_path):
    """Provide a temporary Yggdrasil-like directory structure for isolated tests."""
    for realm in _ACTIVE_REALMS:
        (tmp_path / realm).mkdir()
    return tmp_path
