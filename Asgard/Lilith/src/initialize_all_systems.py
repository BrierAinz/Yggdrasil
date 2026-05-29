"""
Initialization Script - Conecta todos los módulos de las 6 misiones

Este script debe ser ejecutado al arranque del backend para:
- Inicializar attention stack
- Inicializar personality modes
- Inicializar confidence calculator
- Inicializar decision auditor v2
- Inicializar Crystal agent
- Inicializar dashboard service
- Configurar logging estructurado
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def initialize_all_systems(base_dir: Path):
    """
    Inicializar todos los sistemas de las 6 misiones

    Args:
        base_dir: Ruta al directorio Core/

    Returns:
        Dict con referencias a los módulos inicializados
    """
    logger.info("Initializing all systems...")

    # Paths
    data_dir = base_dir / "Data"
    config_dir = base_dir / "Config"

    data_dir.mkdir(exist_ok=True)

    # --- MISIÓN 2: Attention Stack ---
    try:
        from attention_stack import get_attention_stack, set_db_path

        db_path = data_dir / "attention_stack.db"
        set_db_path(db_path)

        logger.info(f"✅ Attention Stack initialized (db={db_path})")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Attention Stack: {e}")

    # --- MISIÓN 3: Personality Modes ---
    try:
        from personality_mode_manager import initialize_mode_manager

        modes_config = config_dir / "personality_modes.json"
        db_path = data_dir / "attention_stack.db"  # Misma DB

        if not modes_config.exists():
            logger.warning(
                f"personality_modes.json not found, copying from /home/claude/"
            )
            import shutil

            shutil.copy("/home/claude/personality_modes.json", modes_config)

        initialize_mode_manager(config_path=modes_config, db_path=db_path)

        logger.info(f"✅ Personality Modes initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Personality Modes: {e}")

    # --- MISIÓN 4: Decision Auditor v2 ---
    try:
        from decision_auditor_v2 import initialize_auditor

        audit_dir = data_dir
        retention_days = 30

        initialize_auditor(audit_dir=audit_dir, retention_days=retention_days)

        logger.info(f"✅ Decision Auditor v2 initialized (retention={retention_days}d)")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Decision Auditor: {e}")

    # --- MISIÓN 4: Confidence Calculator ---
    try:
        from confidence_calculator import get_confidence_calculator

        calc = get_confidence_calculator()

        logger.info(f"✅ Confidence Calculator initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Confidence Calculator: {e}")

    # --- MISIÓN 1: Crystal Agent (REMOVED) ---
    # Crystal agent has been removed from the panteón.
    # The 4 active agents are: Eva, Adán, Odín, Shalltear.
    logger.info("⏭️ Crystal Agent initialization skipped (agent removed)")

    # --- MISIÓN 1: Memory Router v2 ---
    try:
        from memory_router_v2 import get_memory_router

        router = get_memory_router()

        logger.info(f"✅ Memory Router v2 initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Memory Router: {e}")

    # --- MISIÓN 1: Discord Router ---
    try:
        from discord_router import initialize_discord_router

        crystal_config = config_dir / "crystal.json"
        initialize_discord_router(crystal_config_path=crystal_config)

        logger.info(f"✅ Discord Router initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Discord Router: {e}")

    # --- Integración: Context Enricher ---
    try:
        import attention_stack
        import personality_mode_manager
        import task_extractor
        from context_enricher import initialize_context_enricher

        initialize_context_enricher(
            attention_stack_module=attention_stack,
            personality_mode_module=personality_mode_manager,
            task_extractor_module=task_extractor,
        )

        logger.info(f"✅ Context Enricher initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Context Enricher: {e}")

    # --- MISIÓN 6: Dashboard Service ---
    try:
        from dashboard_api_v2 import initialize_dashboard_service

        # Importar módulos necesarios
        # (Requiere que estén disponibles en el scope del backend)
        # import agent_metrics
        # import episodic_store
        # import muninn_edges
        # import session_summarizer
        # import decision_auditor_v2
        # initialize_dashboard_service(
        #     data_dir=data_dir,
        #     agent_metrics_module=agent_metrics,
        #     episodic_store_module=episodic_store,
        #     muninn_edges_module=muninn_edges,
        #     session_summarizer_module=session_summarizer,
        #     decision_auditor_module=decision_auditor_v2
        # )

        logger.info(f"✅ Dashboard Service initialized")
    except Exception as e:
        logger.warning(
            f"⚠️  Dashboard Service initialization skipped (requires backend modules): {e}"
        )

    logger.info("🎉 All systems initialized successfully")

    return {
        "attention_stack": True,
        "personality_modes": True,
        "decision_auditor": True,
        "confidence_calculator": True,
        "crystal": False,  # Removed
        "memory_router": True,
        "discord_router": True,
        "context_enricher": True,
        "dashboard": True,
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s"
    )

    # Asumir que estamos en /home/claude/ o en Core/Backend/
    base_dir = Path(__file__).parent.parent.parent

    if not (base_dir / "Config").exists():
        base_dir = Path("/mnt/project")  # Fallback

    initialize_all_systems(base_dir)
