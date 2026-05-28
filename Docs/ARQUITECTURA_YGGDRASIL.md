# Arquitectura Yggdrasil - Documento Maestro

> **Version:** 2.0  
> **Fecha:** 2026-04-29  
> **Autor:** Völundr + Hermes  
> **Estado:** Post-Remasterizacion

---

## Vision Global

Yggdrasil es un ecosistema de desarrollo personal basado en la mitologia nordica. Cada uno de los 9 reinos tiene un proposito tecnico definido. Nada vive fuera de lugar.

---

## Mapa de Reinos (Estado Actual)

```
Yggdrasil/
|
|-- Asgard/          [CORE] Agentes CLI + monitoreo (4.5 GB, 516 py)
|-- Vanaheim/        [IA] Bots, agentes autonomos (442 KB, 64 py)
|-- Alfheim/         [UI] Prototipos visuales, electronica (47 KB, 1 js)
|-- Svartalfheim/    [DOCS] Conocimiento, guias, arquitectura (2 MB, 21 py)
|-- Muspelheim/      [WIP] Sprint mode, experimentos activos (5 KB, 4 files)
|-- Helheim/         [ARCHIVE] Legacy, cuarentena, cementerio (pesado)
|-- Niflheim/        [RESOURCES] Models, datasets, assets (4.3 GB, 12 files)
|-- Jotunheim/       [GIANT] Proyectos masivos >1 mes (reservado)
|-- Midgard/         [PERSONAL] Apps de uso diario (reservado)
```

---

## Flujo de Vida de un Proyecto

```
[Idea] -> Muspelheim (sprint, 2 semanas max)
            |
            |-- Falla / Abandono -> Helheim (archivar)
            |
            |-- Valida -> [Reino Destino]
                 |
                 |-- Agente/IA -> Vanaheim
                 |-- Dashboard/Monitoreo -> Asgard
                 |-- App personal -> Midgard
                 |-- Prototipo UI -> Alfheim
                 |-- Proyecto >1 mes -> Jotunheim
                 |-- Documentacion -> Svartalfheim
                 |-- Assets/Models -> Niflheim
```

---

## Dependencias Entre Reinos

```
Asgard (Lilith)
    |
    |-- [usa] Niflheim/Models/ (LLM local)
    |-- [usa] Svartalfheim/docs/ (guia de uso)
    |-- [usa] Vanaheim/tools/ (tools externos)
    |
Vanaheim (Bots)
    |
    |-- [usa] Niflheim/Models/ (modelos de IA)
    |-- [contribuye a] Svartalfheim/docs/ (documentacion)
    |
Alfheim (UI)
    |
    |-- [usa] Asgard/ (orquestar comandos)
    |-- [usa] Vanaheim/ (visualizar bots)
    |
Svartalfheim (Docs)
    |
    |-- [documenta] Todos los reinos
    |
Niflheim (Resources)
    |
    |-- [sirve a] Asgard, Vanaheim, Alfheim
```

---

## Reglas de Oro (Post-Remasterizacion)

1. **Sin basura regenerable:** node_modules, pycache, .map, etc. van a cuarentena o se destruyen.
2. **Sin codigo duplicado:** Un modulo vive en un solo lugar. Los demas lo importan.
3. **Sin archivos sueltos:** Todo proyecto tiene README.md y estructura definida.
4. **Sin binarios sin fuente:** Si hay un .exe, debe haber codigo fuente o build script.
5. **Migracion explicita:** Todo cambio de reino se documenta en commit y README.

---

## Metricas de Salud (2026-04-29)

| Metrica | Antes | Despues |
|---------|-------|---------|
| Archivos totales | 62,272 | ~1,500 |
| Tamano total | ~11 GB | 8.8 GB |
| Basura | 60,000+ | 0 (en cuarentena) |
| Proyectos activos | 4 | 7 |
| Reinos vacios | 5 | 2 (Jotunheim, Midgard reservados) |

---

## Puntos de Entrada

| Si quieres... | Ve a... |
|---------------|---------|
| Usar el agente CLI | Asgard/Hermes-Lilith/ |
| Entrenar/poner un bot | Vanaheim/Bots/ |
| Crear una UI | Alfheim/ui-seed/ |
| Leer documentacion | Svartalfheim/docs/ |
| Buscar un modelo LLM | Niflheim/Models/ |
| Ver codigo viejo | Helheim/Archives_Lilith_Legacy_2026-04-29/ |
| Iniciar un sprint | Muspelheim/ |

---

## Proximas Expansiones Planificadas

1. **Jotunheim:** Proyecto de ingestion de datos masiva o training de LLM
2. **Midgard:** Dashboard personal de productividad (calendario + tareas + metricas)
3. **Alfheim:** Orquestador visual con Electron + React
4. **Vanaheim:** Consolidar dependencias Python con requirements.txt unificado
5. **Asgard:** Refactor progresivo del monolito (123k LOC -> modulos)

---

## Contacto

- **Issues / Bugs:** Crear nota en Svartalfheim/issues/
- **Solicitar remasterizacion:** Ejecutar Asgard/scripts/yggdrasil_health_check.py
- **Setup inicial:** Ejecutar setup_yggdrasil.py en raiz

---

*Yggdrasil crece con orden o no crece.*
