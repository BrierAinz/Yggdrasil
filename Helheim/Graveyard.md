<<<<<<< HEAD
# Helheim - Graveyard

Archived and dead projects. Read-only.

| Project | Date | Cause | Size | Notes |
|---------|------|-------|------|-------|
| kohya_ss | 2026-05-21 | Eliminado del monorepo | 6.9 GB | LoRA training, ahora externo |
| Lilith monolito v5.0 | 2026-05-21 | Migrado a módulos | 83 MB | Reemplazado por 8 lilith-* paquetes |
=======
# ⚰️ Helheim Graveyard - Registro de los Caidos

> *Aqui descansan los proyectos que ya no viven. Que su codigo descanse en paz.*

---

## 2026-04-29 - Cuarentena de Basura Regenerable

- **Fecha de muerte**: 2026-04-29 (Remasterizacion)
- **Razon**: Limpieza masiva durante la remasterizacion v2.0
- **Contenido**: node_modules, .pyc, .map, __pycache__, .pytest_cache
- **Tamano original**: ~935MB (59,208 archivos)
- **Lecciones**: Los build artifacts y dependencias siempre se pueden regenerar. Nunca guardarlos en el arbol.
- **Rescatable**: No - todo es regenerable con `npm install`, `pip install`, o builds.
- **Estado**: **ELIMINADO** en limpieza 2026-05-02

---

## 2026-04-29 - Legacy de Lilith (Monolito Original)

- **Fecha de muerte**: 2026-04-29 (Remasterizacion)
- **Razon**: Lilith fue refactorizada de monolito a arquitectura modular. El codigo legacy ya no es compatible.
- **Contenido**: Config_original, Core_Backend (api/core), Core_Frontend, Discord original/v4.2, Telegram original/old
- **Tamano original**: ~920MB (1,606 archivos)
- **Lecciones**: Monolitos escalan mal. La refactorizacion a modulos (Core, Dashboard, MCP, Swarm, Memory) mejoro mantenibilidad y testing dramaticamente. 820+ tests ahora pasan vs ~200 antes.
- **Rescatable**: Parcialmente - algunos configs y prompts pueden reutilizarse. Las lecciones de diseno ya estan en Svartalfheim.
- **Estado**: **ELIMINADO** (tarball purgado 2026-05-11)

---

## 2026-05-02 - Cuarentena de Basura - Limpieza

- **Fecha de muerte**: 2026-05-02
- **Razon**: Purga de espacio en disco. Ni Git trackea estos archivos (estan en .gitignore).
- **Contenido**: Helheim/Quarantine_2026-04-29/ eliminada completamente
- **Lecciones**: Mantener Helheim ligero. Solo guardar codigo fuente, nunca dependencias instaladas.
- **Rescatable**: No
- **Estado**: **ELIMINADO**

---

## 2026-05-11 - Purga Completa de Helheim (5.2GB liberados)

- **Fecha**: 2026-05-11
- **Razon**: 5.2GB de datos legacy sin referencias activas fuera de Helheim
- **Contenido eliminado**:
  - `Archives_Lilith_Legacy_2026-04-29.tar.gz` (814MB) — comprimido del monolito
  - `Lilith_backup_pre_refactor_20260403_145209.tar.gz` (4.4GB) — backup pre-refactor
  - `Archives_Lilith_Monolith/` (1.5MB, 126 archivos) — monolito descomprimido
  - `Hermes-Lilith_v4_legacy/` (27MB, 247 archivos) — código v4 legacy
  - `Dashboards_legacy/` (346KB, 19 archivos) — dashboards viejos
- **Lecciones**: Los backups legacy dejan de ser útiles después de que el código refactorizado está en producción y estable.
- **Rescatable**: No — todo está documentado aquí y el código vive en Asgard/Lilith/
- **Estado**: **ELIMINADO**

---

*Cripta de Proyectos - Aqui descansan los caídos*
>>>>>>> origin/main
