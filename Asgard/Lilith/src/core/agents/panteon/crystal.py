"""Crystal - ELIMINADO. Ya no existe. Importar lanzará error explicativo."""


def get_crystal_agent(*args, **kwargs):
    raise NotImplementedError(
        "CrystalAgent fue eliminado del panteón (Discord desactivado). "
        "Usa los agentes activos: EvaAgent, AdanAgent, OdinAgent, ShalltearAgent"
    )


__all__ = ["get_crystal_agent"]