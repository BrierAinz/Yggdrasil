"""
Panteón de Agentes - Lilith v5.0

Agentes activos: Eva, Adán, Odín, Shalltear
Agentes eliminados: Albedo, Archivero, Crystal (stubs con NotImplementedError)
"""

from .adan import AdanAgent
from .eva import EvaAgent
from .odin import OdinAgent
from .shalltear import ShalltearAgent

__all__ = [
    "AdanAgent",
    "EvaAgent",
    "OdinAgent",
    "ShalltearAgent",
]