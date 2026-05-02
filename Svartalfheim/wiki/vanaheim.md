---
name: Vanaheim
realm: Vanaheim
status: Activo
stack:
  - Python 3.11+
  - Discord API
  - Telegram API
  - SQLite
dependencies:
  - Niflheim/Models (AI models)
  - Asgard/Hermes-Lilith (core engine)
  - Svartalfheim/docs (documentation)
---

# 🌿 Vanaheim — Reino de los Agentes de IA

> *Donde los Vanir cultivan la inteligencia que fluye como ríos.*

## 📜 Propósito

Vanaheim es el reino de los bots y agentes autónomos — las entidades que interactúan con el mundo exterior a través de plataformas como Discord y Telegram. Los Vanir son los diplomáticos del ecosistema, extendiendo la inteligencia de Lilith hacia canales de comunicación externos.

## 🏗️ Arquitectura

```
Vanaheim/
└── Bots/
    ├── discord_bot/      # Bot de Discord con comandos slash
    ├── telegram_bot/     # Bot de Telegram con commands
    └── shared/          # Lógica compartida entre plataformas
```

## 🔧 Componentes Clave

| Componente | Función |
|-----------|---------|
| Discord Bot | Interacción en canales de Discord |
| Telegram Bot | Interacción en chats de Telegram |
| Shared Utils | Lógica de intercomunicación y parsing |

## 🔗 Dependencias

- **Asgard**: Motor Lilith para procesamiento de lenguaje
- **Niflheim**: Modelos de IA para inferencia
- **Svartalfheim**: Documentación generada por bots

## 📊 Estado

- **Tamaño**: ~442 KB, 64 archivos Python
- **Integración**: Conecta con Lilith Core via API
- **Expansión planeada**: Framework unificado de bots con requirements.txt consolidado

## ⚠️ Notas

- Los bots consumen la API de Asgard para_orquestar comandos
- Vanaheim contribuye documentación a Svartalfheim
- El framework de bots está pendiente de consolidación
