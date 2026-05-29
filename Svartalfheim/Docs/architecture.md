# Arquitectura de Yggdrasil

<<<<<<< HEAD
## Vision General

Yggdrasil es un ecosistema de proyectos personales organizado bajo una metafora de 9 reinos nordicos. Cada reino tiene un proposito definido y reglas de interaccion claras.

## Reinos y Propositos

| Reino         | Proposito                              | Estado        |
|---------------|----------------------------------------|---------------|
| Asgard        | Tecnologia core, Lilith, Hermes        | Activo        |
| Vanaheim      | Agentes de IA y bots                   | Activo        |
| Alfheim       | Prototipos de UI y dashboards          | Activo        |
| Svartalfheim  | Documentacion y conocimiento           | Activo        |
| Muspelheim    | Desarrollo activo / WIP                | Variable      |
| Niflheim      | Recursos, assets, modelos LLM          | Activo        |
| Midgard       | Apps personales del usuario            | Activo        |
| Jotunheim     | Proyectos masivos                      | Variable      |
| Helheim       | Archivo, legacy, codigo obsoleto       | Activo        |

## Flujo de Datos

```
Usuario -> Lilith CLI (Asgard) -> Vanaheim Bots
                                -> Alfheim Dashboard (via API)
                                -> Niflheim Models
```

## Convenciones

- Todo proyecto nuevo debe asignarse a un reino.
- Los reinos no deben tener dependencias circulares.
- Asgard es el nucleo; otros reinos consumen su API.
=======
> **Este archivo es un redirect.** La documentación maestra de arquitectura
> se encuentra en: [`ARQUITECTURA_YGGDRASIL.md`](./ARQUITECTURA_YGGDRASIL.md)

Para la estructura completa de reinos, dependencias, tooling stack y métricas,
consulta el documento maestro enlazado arriba.
>>>>>>> origin/main
