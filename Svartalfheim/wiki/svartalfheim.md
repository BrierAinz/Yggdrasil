---
name: Svartalfheim
realm: Svartalfheim
status: Activo
stack:
  - Markdown
  - YAML (frontmatter)
  - TOML (configs)
  - Python (scripts de validación)
dependencies:
  - Todos los reinos (documenta a todos)
---

# 🔨 Svartalfheim — Reino del Conocimiento y la Documentación

> *Donde los Enanos forjan las runas que preservan la sabiduría de los Nueve Mundos.*

## 📜 Propósito

Svartalfheim es el archivo vivo del ecosistema Yggdrasil — aquí se forja toda la documentación, guías, arquitectura, ADRs, runbooks y conocimiento. Sin los Enanos, los demás reinos olvidarían cómo funcionan sus propias creaciones.

## 🏗️ Arquitectura

```
Svartalfheim/
├── Docs/
│   ├── architecture.md          # Arquitectura del ecosistema
│   ├── ARQUITECTURA_YGGDRASIL.md # Documento maestro v2.0
│   ├── plans/                   # Planes de desarrollo
│   └── wiki/                    ← ESTE DIRECTORIO
│       ├── [9 realm pages]       # Wiki de cada reino
│       ├── adrs/                 # Architecture Decision Records
│       ├── runbooks/             # Procedimientos operativos
│       ├── templates/            # Templates para nuevos proyectos
│       ├── cross-realm.md        # Índice de dependencias
│       └── glossary.md           # Glosario del ecosistema
├── Archives_Lilith_Monolith/    # Archivo histórico del monolito
└── README.md
```

## 🔧 Componentes Clave

| Componente | Función |
|-----------|---------|
| Wiki Pages | Documentación de cada reino |
| ADRs | Decisiones arquitectónicas registradas |
| Runbooks | Procedimientos operativos paso a paso |
| Templates | Plantillas para nuevos proyectos |
| Cross-Realm Map | Índice de dependencias entre reinos |
| Glossary | Glosario terminológico del ecosistema |

## 🔗 Dependencias

- **Todos los reinos**: Svartalfheim documenta a todos

## 📊 Estado

- **Tamaño**: ~2 MB, 21 archivos Python + docs
- **Wiki**: Completa con 9 páginas de reinos
- **ADRs**: 10 registros de decisiones arquitectónicas
- **Runbooks**: Deploy, debug, contribución

## 🔥 Reglas de Forja

1. Todo proyecto nuevo debe documentarse aquí
2. Formato preferido: Markdown con frontmatter YAML
3. Los ADRs son inmutables una vez aceptados
4. Versionar documentación importante junto con el código
