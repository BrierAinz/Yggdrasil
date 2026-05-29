# Yggdrasil Docs

Documentacion oficial del ecosistema Yggdrasil — BrierStudios.

---

## Guias

| Documento | Descripcion |
|-----------|-------------|
| [Quick Start](QUICKSTART.md) | Instalacion y primeros pasos |
| [Nine Realms](REALMS.md) | Guia completa de los 9 realms |
| [Lilith Guide](LILITH.md) | Todo sobre el agente Lilith |
| [API Reference](API.md) | Endpoints de los servicios |
| [Changelog](CHANGELOG.md) | Historial de versiones |

## Recursos

| Recurso | Descripcion |
|---------|-------------|
| [GitHub](https://github.com/BrierAinz/Yggdrasil) | Repositorio principal |
| [brierstudios.com](https://brierstudios.com) | Sitio web principal |
| [docs.brierstudios.com](https://docs.brierstudios.com) | Este sitio de docs |

## Arquitectura Rapida

```
Yggdrasil (v5.1.0)
├── Asgard      → 8 paquetes lilith-* (2 activos)
├── Vanaheim    → AI Agents (esqueleto)
├── Alfheim     → UI (referenciado)
├── Svartalfheim → Docs, scripts, plans, wiki
├── Muspelheim  → Horror-GameMaster (Fases 1-4)
├── Niflheim    → Assets (gitignored)
├── Helheim     → Archive (solo lectura)
├── Jotunheim   → Massive (reservado)
└── Midgard     → Personal
```

## Comandos Rapidos

```bash
python ygg.py              # CLI principal
python lilith_agent.py     # Agente IA
python lilith_cli.py chat  # Chat con Lilith
```
