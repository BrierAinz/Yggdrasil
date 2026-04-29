import pytest
import sys
from pathlib import Path

YGGDRASIL_ROOT = Path(__file__).parent.parent.resolve()

for realm in ["Asgard", "Vanaheim", "Svartalfheim"]:
    realm_path = YGGDRASIL_ROOT / realm
    if realm_path.exists() and str(realm_path) not in sys.path:
        sys.path.insert(0, str(realm_path))


@pytest.fixture
def yggdrasil_root():
    return YGGDRASIL_ROOT
