---
adr_id: ADR-007
title: MCP Protocol para Tool Discovery
status: Accepted
date: 2026-04-29
decision_makers:
  - Völundr
  - Hermes
---

# 🔗 ADR-007: MCP Protocol para Tool Discovery

## Context

Lilith necesita conectar con herramientas externas (filesystem, browser, terminal, desktop) de forma dinámica. Hardcodear cada tool es rígido — se necesita un protocolo estándar para descubrir y ejecutar tools de forma extensible.

## Decision

Implementar **Model Context Protocol (MCP)** según la especificación `2024-11-05`:

1. **JSON-RPC 2.0**: Protocolo de comunicación con servidores MCP
2. **Client**: `MCPClient` que se conecta a servidores MCP via stdio/SSE
3. **Manager**: `MCPManager` que gestiona múltiples clientes
4. **Tipos**: Dataclasses para `MCPTool`, `MCPResource`, `MCPPrompt`, `MCPToolParameter`
5. **Métodos**: Initialize, ping, tools/list, tools/call, resources/list, resources/read
6. **Dynamic Tools**: Tools descubiertas via MCP se registran automáticamente en `DynamicToolRegistry`

Flujo:
```
Lilith Orchestrator
    → MCPManager
        → MCPClient (stdio/SSE)
            → MCPServer (filesystem, browser, etc.)
                → Tool execution
```

## Consequences

### Positivas
- **Extensible**: Cualquier servidor MCP se integra sin código
- **Estandarizado**: Sigue la especificación oficial de Anthropic
- **Discovery**: Tools se descubren dinámicamente al conectar
- **Seguro**: Sandboxing por proceso, no ejecución directa

### Negativas
- **Latencia**: Comunicación IPC via stdio/SSE agrega overhead
- **Complejidad**: JSON-RPC 2.0 requiere handling de errores robusto
- **Dependencia**: Requiere que los servidores MCP estén corriendo
- **Debugging**: Más difícil de debuggear que tools nativas
