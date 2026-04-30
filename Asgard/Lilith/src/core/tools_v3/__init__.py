"""
Lilith 3.0 — Capa de tools unificada (Fase 1).
Protocolo LilithTool, ToolRegistryV3, y tools de sistema.
"""
from pathlib import Path

from .agent_tools import (
    DelegateAdanTool,
    DelegateEvaTool,
    DelegateLocalIrreverentTool,
    DelegateLuciferTool,
    DelegateOdinTool,
)
from .chained_tool import ExecuteChainedTool
from .council_tool import ActivateCouncilTool
from .cursor_cli_tool import CursorCLITool
from .exec_tool import ExecTool
from .file_edit_tool import FileEditTool
from .file_read_tool import FileReadTool
from .fun_tools import ChisteTool, MemeTool
from .gather_directory_tool import GatherDirectoryTool
from .generate_reply_tool import GenerateReplyTool
from .kimi_cli_tool import KimiCLITool
from .list_directory_tool import ListDirectoryTool
from .memory_tools import SearchSemanticMemoryTool, StoreInteractionTool
from .owner_system_tool import OwnerSystemTool
from .project_tool import ProjectTool
from .protocol import LilithTool, ToolResult
from .registry import ToolRegistryV3
from .self_improvement_tool import SelfImproveTool
from .shalltear_tool import DelegateShalltearTool, ShalltearParseTool
from .web_search_tool import WebSearchTool
from .yield_tool import YieldToAgentTool

__all__ = [
    "LilithTool",
    "ToolResult",
    "ToolRegistryV3",
    "FileReadTool",
    "ListDirectoryTool",
    "FileEditTool",
    "GenerateReplyTool",
    "DelegateEvaTool",
    "DelegateAdanTool",
    "DelegateLuciferTool",
    "CursorCLITool",
    "ChisteTool",
    "MemeTool",
    "GatherDirectoryTool",
    "DelegateOdinTool",
    "DelegateLocalIrreverentTool",
    "SearchSemanticMemoryTool",
    "StoreInteractionTool",
    "StoreSemanticFactTool",
    "LoreExtractorTool",
    "SelfImproveTool",
    "ExecuteChainedTool",
    "ProjectTool",
    "OwnerSystemTool",
    "KimiCLITool",
    "create_default_registry",
    "create_trusted_registry",
    "WebSearchTool",
    "ExecTool",
    "YieldToAgentTool",
    "DelegateShalltearTool",
    "ShalltearParseTool",
    "ActivateCouncilTool",
]


def create_trusted_registry(project_root: Path) -> ToolRegistryV3:
    """Registro limitado para role=trusted: solo generate_reply, chiste y meme. Sin archivos ni agentes pesados."""
    reg = ToolRegistryV3()
    reg.register(GenerateReplyTool())
    reg.register(ChisteTool())
    reg.register(MemeTool())
    return reg


def _timeout_from_config(root: Path, key: str, default: int = 120) -> int:
    """3.7/3.8: Lee timeout desde Config/tools.json (timeouts) o Config/memory.json."""
    try:
        from src.core.json_safe import safe_load

        tools_path = root / "Config" / "tools.json"
        if tools_path.exists():
            tools_cfg = safe_load(tools_path, default={})
            timeouts = (
                (tools_cfg or {}).get("timeouts")
                if isinstance(tools_cfg, dict)
                else None
            )
            if isinstance(timeouts, dict) and key in timeouts:
                return max(30, int(timeouts[key]) or default)
        cfg = safe_load(root / "Config" / "memory.json", default={})
        if isinstance(cfg, dict) and key in cfg:
            return max(30, int(cfg[key]) or default)
    except Exception:
        pass
    return default


def create_default_registry(project_root: Path) -> ToolRegistryV3:
    """Crea un ToolRegistryV3 con tools por defecto. B.2: lazy loading (instanciar en primer uso)."""
    root = Path(project_root)
    reg = ToolRegistryV3()
    reg.register_lazy("read_file", lambda: FileReadTool(root))
    reg.register_lazy("list_directory", lambda: ListDirectoryTool(root))
    reg.register_lazy("edit_file", lambda: FileEditTool(root))
    reg.register_lazy("generate_reply", lambda: GenerateReplyTool())
    reg.register_lazy("delegate_eva", lambda: DelegateEvaTool())
    reg.register_lazy("delegate_adan", lambda: DelegateAdanTool())
    reg.register_lazy("delegate_lucifer", lambda: DelegateLuciferTool())
    reg.register_lazy("delegate_odin", lambda: DelegateOdinTool())
    reg.register_lazy(
        "delegate_local_irreverent", lambda: DelegateLocalIrreverentTool(root)
    )
    reg.register_lazy("gather_directory", lambda: GatherDirectoryTool(root))
    reg.register_lazy("delegate_cursor", lambda: CursorCLITool(root))
    reg.register_lazy("search_semantic_memory", lambda: SearchSemanticMemoryTool(root))
    reg.register_lazy("store_interaction", lambda: StoreInteractionTool(root))

    def _make_store_semantic_fact():
        from .memory_tools import StoreSemanticFactTool

        return StoreSemanticFactTool(root)

    reg.register_lazy("store_semantic_fact", _make_store_semantic_fact)

    def _make_lore_extractor():
        from .lore_extractor_tool import LoreExtractorTool

        return LoreExtractorTool(root)

    reg.register_lazy("lore_extractor", _make_lore_extractor)
    reg.register_lazy("self_improve", lambda: SelfImproveTool(root))
    reg.register_lazy("execute_chained", lambda: ExecuteChainedTool(root, reg))
    reg.register_lazy("project", lambda: ProjectTool(root))
    reg.register_lazy("owner_system_action", lambda: OwnerSystemTool(root))
    reg.register_lazy("web_search", lambda: WebSearchTool())
    reg.register_lazy("exec", lambda: ExecTool(root))
    reg.register_lazy("yield_to_agent", lambda: YieldToAgentTool())
    reg.register_lazy("delegate_shalltear", lambda: DelegateShalltearTool())
    reg.register_lazy("shalltear_parse_pc", lambda: ShalltearParseTool())
    reg.register_lazy(
        "delegate_kimi_cli",
        lambda: KimiCLITool(
            root, timeout=_timeout_from_config(root, "timeout_kimi_seconds", 120)
        ),
    )

    # Browser tools (Playwright) — lazy para no iniciar engine al importar
    def _browser_goto():
        from src.core.tools.browser.browser_tool import BrowserGotoTool

        return BrowserGotoTool()

    def _browser_click():
        from src.core.tools.browser.browser_tool import BrowserClickTool

        return BrowserClickTool()

    def _browser_fill():
        from src.core.tools.browser.browser_tool import BrowserFillTool

        return BrowserFillTool()

    def _browser_scroll():
        from src.core.tools.browser.browser_tool import BrowserScrollTool

        return BrowserScrollTool()

    def _browser_extract():
        from src.core.tools.browser.browser_tool import BrowserExtractTool

        return BrowserExtractTool()

    reg.register_lazy("browser_goto", _browser_goto)
    reg.register_lazy("browser_click", _browser_click)
    reg.register_lazy("browser_fill", _browser_fill)
    reg.register_lazy("browser_scroll", _browser_scroll)
    reg.register_lazy("browser_extract", _browser_extract)
    # PC Agent tools (Telegram NL + owner DM)
    from .pc_agent_tools import (
        PCBatchTool,
        PCCopyTool,
        PCDeleteTool,
        PCExecTool,
        PCListTool,
        PCMkdirTool,
        PCMoveTool,
        PCWriteFileTool,
    )

    reg.register_lazy("pc_list", lambda: PCListTool(root))
    reg.register_lazy("pc_mkdir", lambda: PCMkdirTool(root))
    reg.register_lazy("pc_move", lambda: PCMoveTool(root))
    reg.register_lazy("pc_copy", lambda: PCCopyTool(root))
    reg.register_lazy("pc_delete", lambda: PCDeleteTool(root))
    reg.register_lazy("pc_write_file", lambda: PCWriteFileTool(root))
    reg.register_lazy("pc_exec", lambda: PCExecTool(root))
    reg.register_lazy("pc_batch", lambda: PCBatchTool(root))
    reg.register_lazy("activate_council", lambda: ActivateCouncilTool())
    return reg
