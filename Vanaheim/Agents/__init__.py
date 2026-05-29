"""Agentes del Panteón ejecutándose en Vanaheim."""

import sys
from pathlib import Path


# Asegurar que el directorio de Agents está en el path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from adan_vanaheim import AdanAgent
except ImportError as e:
    import logging

    logging.warning(f"Could not import AdanAgent: {e}")
    AdanAgent = None

try:
    from eva_vanaheim import EvaAgent
except ImportError as e:
    import logging

    logging.warning(f"Could not import EvaAgent: {e}")
    EvaAgent = None

try:
    from odin_vanaheim import OdinAgent
except ImportError as e:
    import logging

    logging.warning(f"Could not import OdinAgent: {e}")
    OdinAgent = None

__all__ = ["AdanAgent", "EvaAgent", "OdinAgent"]
