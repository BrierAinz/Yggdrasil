---
name: Muspelheim
realm: Muspelheim
status: Variable
stack:
  - Variable (se define por sprint)
dependencies:
  - Asgard (core API)
  - Svartalfheim (documentación de resultados)
---

# 🔥 Muspelheim — Reino del Desarrollo Activo (WIP)

> *Donde Surtr forja en llamas lo que aún no existe — cada chispa es un experimento.*

## 📜 Propósito

Muschelheim es la cámara de combustión de Yggdrasil. Todo proyecto nuevo entra aquí como un sprint de máximo 2 semanas. Si sobrevive, migra a su reino destino. Si no, cae a Helheim.

## 🏗️ Arquitectura

```
Muspelheim/
└── [proyecto-sprint]/    # Proyecto temporal en desarrollo
```

## 🔧 Componentes Clave

| Componente | Función |
|-----------|---------|
| Sprint Projects | Experimentos de ≤2 semanas |
| Prototipos | Pruebas de concepto rápidas |

## 🔗 Dependencias

- **Asgard**: API core para integraciones
- **Svartalfheim**: Documentación de resultados y lecciones

## 📊 Estado

- **Tamaño**: ~5 KB, 4 archivos
- **Estado**: Variable — se llena y vacía con cada sprint
- **Flujo**: Idea → Sprint → Validación → Reino destino o Helheim

## 🔥 Reglas del Fuego

1. Todo proyecto en Muspelheim tiene deadline de 2 semanas
2. Al finalizar, se decide: migrar a reino destino o archivar en Helheim
3. No se acumulan proyectos muertos — se archivan o se destruyen
4. Cada sprint debe generar documentación en Svartalfheim
