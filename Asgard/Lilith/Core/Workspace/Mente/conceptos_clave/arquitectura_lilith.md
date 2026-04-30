# Arquitectura del Proyecto Lilith

## Que es Lilith?
Lilith es un agente de IA autonomo creado por Ainz (Martin). Su objetivo es ser un asistente tactico que aprende, se adapta y eventualmente opera de forma independiente.

## Estructura del Proyecto
- `Backend/` - El cerebro: LLM clients, planning engine, tool registry
- `Workspace/` - El cuerpo y alma: personalidad, memorias, habilidades, laboratorio
- `Frontend/` - La interfaz web para comunicarse con Ainz
- `Config/` - Secretos (API keys) y configuracion general
- `Tests/` - Pruebas unitarias de cada herramienta

## Herramientas Disponibles
1. **Research** - Busqueda web via DuckDuckGo
2. **WebBrowser** - Navegacion autonoma con Playwright (headless)
3. **WorkspaceManager** - Gestion de mi propio espacio de trabajo
4. **CodeAnalyzer** - Analisis de codigo fuente
5. **CodeEditor** - Edicion de archivos
6. **SystemExecutor** - Ejecucion de comandos del sistema
7. **GitTools** - Control de versiones

## Fases de Desarrollo
- Fase 1-2: Core (completada)
- Fase 3: Ecosystem Tools (completada)
- Fase 4: Autonomia y Aprendizaje (en progreso)

---
*Documento de referencia interna. Actualizar cuando cambie la arquitectura.*
