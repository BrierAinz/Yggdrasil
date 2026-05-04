import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Make all active Yggdrasil realms importable in tests
# ---------------------------------------------------------------------------
YGGDRASIL_ROOT = Path(__file__).parent.parent.resolve()

# Active realms with installable packages
_ACTIVE_REALMS = ["Asgard", "Vanaheim", "Muspelheim", "Alfheim", "Svartalfheim", "Midgard"]

for realm in _ACTIVE_REALMS:
    realm_path = YGGDRASIL_ROOT / realm
    if realm_path.exists() and str(realm_path) not in sys.path:
        sys.path.insert(0, str(realm_path))


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
