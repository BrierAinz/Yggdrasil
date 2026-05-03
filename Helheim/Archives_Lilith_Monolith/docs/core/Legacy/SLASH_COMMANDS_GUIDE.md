# Guía de Slash Commands - Discord

**Versión:** 4.1  
**Fecha:** 2026-03-21

---

## Introducción

Lilith usa Discord Slash Commands para proporcionar una UX moderna con:
- Autocompletado
- Validación de parámetros
- Descripciones inline
- Organización por grupos

---

## Comandos Disponibles

### 🧠 Memoria

#### `/memoria`
Gestiona la memoria de Lilith.

**Parámetros:**
- `action`: Acción a realizar
  - `Buscar hechos` - Busca en memoria semántica
  - `Listar episodios` - Muestra timeline episódica
  - `Exportar memoria` - Genera archivo de exportación
  - `Estadísticas` - Muestra stats de memoria
- `query`: Texto de búsqueda (solo para "Buscar")

**Ejemplos:**
```
/memoria action:Buscar hechos query:python
/memoria action:Listar episodios
```

#### `/patrones`
Muestra patrones de automatización aprendidos.

**Sin parámetros.**

Muestra:
- Patrones aprendidos
- Patrones sugeridos con confianza

#### `/feedback`
Envía feedback sobre la última respuesta.

**Parámetros:**
- `rating`: Valoración (1-5 estrellas)
- `comment`: Comentario opcional

**Ejemplo:**
```
/feedback rating:5 comment:Muy útil, gracias!
```

---

### 📋 Tasks

#### `/tasks`
Gestiona tareas programadas.

**Parámetros:**
- `action`: Acción a realizar
  - `Listar tasks` - Lista todas las tasks
  - `Pausar task` - Pausa una task
  - `Reanudar task` - Reanuda una task
  - `Ejecutar ahora` - Ejecuta inmediatamente
- `name`: Nombre de la task (para pause/resume/run)

**Autocompletado:** Sugiere nombres de tasks existentes.

**Ejemplos:**
```
/tasks action:Listar
/tasks action:Pausar name:auto-learn
/tasks action:Ejecutar ahora name:backup
```

#### `/monitores`
Gestiona monitores de fuentes.

**Parámetros:**
- `action`: Acción
  - `Listar monitores` - Lista monitores activos
  - `Añadir monitor` - Añade nueva URL
  - `Eliminar monitor` - Elimina un monitor
- `url`: URL a monitorear (para add)
- `interval`: Intervalo en segundos (default: 300)

**Ejemplos:**
```
/monitores action:Listar
/monitores action:Añadir url:https://example.com interval:600
```

---

### ⚙️ Sistema (Owner Only)

#### `/backup`
Gestiona backups del sistema.

**Requiere:** Permisos de administrador

**Parámetros:**
- `action`: Acción
  - `Crear backup` - Genera nuevo backup
  - `Listar snapshots` - Lista backups disponibles
  - `Restaurar snapshot` - Restaura desde backup
- `snapshot`: Nombre del snapshot (para restore)

**Autocompletado:** Lista snapshots disponibles.

**Ejemplos:**
```
/backup action:Crear
/backup action:Listar
/backup action:Restaurar snapshot:backup-20240321.zip
```

#### `/audit`
Exporta logs de auditoría.

**Requiere:** Permisos de administrador

**Parámetros:**
- `date`: Fecha (YYYY-MM-DD, default: hoy)
- `format`: Formato (JSON o Texto)

**Ejemplo:**
```
/audit date:2024-03-21 format:JSON
```

#### `/status`
Muestra estado del sistema.

**Requiere:** Permisos de administrador

Muestra:
- Estado de API, Core, Base de datos
- Uptime
- Estadísticas de uso

---

### 📚 Ayuda

#### `/help`
Muestra ayuda interactiva.

**Sin parámetros.**

Muestra un embed con botones para navegar entre categorías:
- Inicio
- Memoria
- Tasks
- Sistema (solo owners)

---

## Permisos

| Comando | Rol |
|---------|-----|
| `/memoria` | Todos |
| `/patrones` | Todos |
| `/feedback` | Todos |
| `/tasks` | Trusted+ |
| `/monitores` | Trusted+ |
| `/backup` | Owner |
| `/audit` | Owner |
| `/status` | Owner |
| `/help` | Todos |

---

## Autocompletado

Algunos comandos ofrecen autocompletado:

### `/tasks name:`
Sugiere tasks existentes:
- auto-learn
- backup
- cleanup
- sync

### `/backup snapshot:`
Sugiere snapshots disponibles:
- backup-20240321.zip
- backup-20240320.zip
- etc.

---

## Errores Comunes

### "Comando no encontrado"
- Los comandos pueden tardar hasta 1 hora en sincronizarse globalmente
- En desarrollo, se sincronizan inmediatamente al servidor

### "No tienes permiso"
- Algunos comandos requieren rol específico
- Verificar permisos con `/help`

### "Error al ejecutar"
- La API puede estar caída
- Verificar logs del servidor

---

## Implementación

Los comandos están definidos en:

```
Discord/commands/
├── __init__.py
├── memory_commands.py
├── task_commands.py
├── system_commands.py
└── help_command.py
```

### Agregar nuevo comando

```python
@bot.tree.command(name="micomando", description="Descripción")
@app_commands.describe(parametro="Descripción del parámetro")
async def micomando(interaction: discord.Interaction, parametro: str):
    await interaction.response.defer(thinking=True)
    # ... lógica ...
    await interaction.followup.send("Resultado")
```

### Autocompletado

```python
@micomando.autocomplete('parametro')
async def autocomplete_parametro(interaction: discord.Interaction, current: str):
    opciones = ["opcion1", "opcion2"]
    return [
        app_commands.Choice(name=opt, value=opt)
        for opt in opciones if current.lower() in opt.lower()
    ][:25]
```

---

## Testing

```bash
cd Lilith/Discord
python -m pytest tests/test_slash_commands.py -v
```

### Tests incluidos
- Creación de comandos
- Autocompletado
- Permisos
- Respuestas

---

## Referencias

- [Discord.py Slash Commands](https://discordpy.readthedocs.io/en/stable/interactions/api.html)
- [Discord API - Application Commands](https://discord.com/developers/docs/interactions/application-commands)
