---
sidebar_position: 8
title: Reglas de Yggdrasil
---

# Reglas de Yggdrasil

Principios fundamentales que gobiernan el ecosistema.

## 1. Un Árbol, Nueve Reinos

Todo componente pertenece a un reino. No hay código huérfano. Si no sabes dónde poner algo, pregúntate: ¿qué responsabilidad tiene?

## 2. Modularidad Radical

Cada paquete `lilith-*` es independiente. Puede instalarse, versionarse y testearse solo. Las dependencias son explícitas y unidireccionales.

## 3. Los Tests Son la Verdad

Si no tiene test, no existe. Los tests son la especificación viva del comportamiento esperado.

## 4. La Configuración Es Código

`YggdrasilConfig` es un dataclass, no un diccionario mágico. Los tipos son la documentación.

## 5. La Memoria Es Persistente

Cada interacción con un agente se almacena. Nada se pierde. La memoria es la base de la inteligencia.

## 6. Los Logs Son Observables

Cada decisión del agente se loggea. Si no puedes auditarlo, no puedes confiar en ello.

## 7. El Fuego y el Hielo

Muspelheim (fuego) crea. Niflheim (hielo) preserva. El equilibrio entre ambos es la estabilidad.

## 8. Sin Dependencias Circulares

Los reinos no se miran al espejo. Si A depende de B, B no puede depender de A.

## 9. El Árbol Crece

Yggdrasil no se termina. Se evoluciona. Cada versión es una rama nueva, no un reemplazo.
