# SEBAS V2 - Enhanced Mayordomo IA

## 🚀 Nuevas Características

### ✅ Sistema de Memoria
- Guarda todas las conversaciones en `memory/conversations.json`
- Mantiene contexto entre sesiones
- Comando `@memory` para ver historial
- Comando `@clear` para limpiar memoria

### ✅ Lectura de Archivos
- Comando `@read <archivo>` para analizar código
- Seguridad: Solo puede leer archivos en D:\Proyectos
- Ejemplo: `@read D:\Proyectos\StoryEngine_Project\Design\00_VISION.md`

### ✅ Interfaz Mejorada
- Indicador de LLM activo (Ollama)
- Botones de memoria visibles
- Timestamp en mensajes
- Mejor scroll y UX

## 📋 Uso

### Iniciar
```powershell
cd "D:\Proyectos\Yggdrasil IA\Svartalfheim"
python sebas_gui.py
```

### Comandos Especiales
```
@read <archivo>    # Leer y analizar archivo
@memory            # Ver conversaciones recientes
@clear             # Limpiar toda la memoria
```

### Ejemplos
```
Tú: @read D:\Proyectos\README.md
SEBAS: [Analiza el archivo y te lo muestra]

Tú: explica este diseño
SEBAS: [Responde basándose en el archivo leído]

Tú: @memory
SEBAS: [Muestra historial de conversación]
```

## 🧠 Memoria Persistente

SEBAS ahora recuerda:
- Todas las conversaciones previas
- Contexto de archivos leídos
- Preferencias mencionadas

La memoria se guarda automáticamente en `memory/conversations.json`.

## 🎯 Diferencias con SEBAS V1

| Feature | V1 | V2 |
|---------|----|----|
| Memoria | ❌ | ✅ Persistente |
| Leer archivos | ❌ | ✅ @read |
| UI moderna | ❌ | ✅ Botones + indicadores |
| Comandos especiales | ❌ | ✅ @read, @memory, @clear |
| Contexto entre sesiones | ❌ | ✅ Automático |

## 📁 Estructura

```
Svartalfheim/
├── sebas_gui.py           # Entry point
├── gui/
│   ├── main_window.py     # GUI mejorada
│   └── simple_agent.py    # Agent con memoria
├── core/
│   └── memory.py          # Memory manager
├── capabilities/
│   └── file_reader.py     # File reading
└── memory/
    ├── conversations.json # Historial (auto-creado)
    └── context.json       # Contexto (auto-creado)
```

## 🔧 Requisitos

- Ollama corriendo (`ollama serve`)
- Modelo llama3.1:8b instalado
- Python 3.8+
- CustomTkinter, aiohttp

---

**SEBAS V2 está listo para asistir, Ainz.** 🤵
