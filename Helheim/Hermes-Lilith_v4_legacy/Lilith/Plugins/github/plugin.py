"""
GitHub Plugin para Lilith
========================
Integración con GitHub - búsqueda de repos, issues, PRs.
"""
from Lilith.Plugins.plugin_manager import Plugin, PluginCapability

# Tools del plugin
GITHUB_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "github_search_repos",
            "description": "Busca repositorios en GitHub",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query de búsqueda (ej: 'Lilith assistant python')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Máximo de resultados (default: 5)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_get_repo_info",
            "description": "Obtiene información de un repositorio",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Owner del repo"},
                    "repo": {"type": "string", "description": "Nombre del repo"},
                },
                "required": ["owner", "repo"],
            },
        },
    },
]


def get_plugin() -> Plugin:
    """Retorna la instancia del plugin."""
    return Plugin(
        id="github",
        name="GitHub Integration",
        version="1.0.0",
        description="Integración con GitHub para buscar repos, ver issues y más",
        author="Lilith",
        capabilities=[
            PluginCapability.WEB,
            PluginCapability.INTEGRATION,
            PluginCapability.TOOL,
        ],
        tools=GITHUB_TOOLS,
        config={"api_token": "", "default_branch": "main"},  # Opcional para rate limits
    )


# Implementación de las tools (para usar con API real)
async def search_repos(query: str, max_results: int = 5):
    """Busca repositorios en GitHub."""
    # En producción usarías requests con la API de GitHub
    return {
        "query": query,
        "results": [],
        "message": "GitHub API integration - configure token for real results",
    }


async def get_repo_info(owner: str, repo: str):
    """Obtiene info de un repo."""
    return {
        "owner": owner,
        "repo": repo,
        "message": "GitHub API integration - configure token for real results",
    }
