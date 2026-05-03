# Pruebas 3.7 — Copy-paste

Copia y pega en este orden. (Primero arranca Lilith; luego URLs; luego mensajes en Discord.)

---

## 1. Arrancar Lilith

En la raíz del proyecto (carpeta `Lilith`), doble clic o en CMD:

```
D:\Proyectos\Yggdrasil\Asgard\Lilith\arranque_lilith.bat
```

O manualmente en **dos terminales**:

**Terminal 1 — API:**
```
cd /d D:\Proyectos\Yggdrasil\Asgard\Lilith\Core
set PYTHONPATH=D:\Proyectos\Yggdrasil\Asgard\Lilith\Core
python -m Backend.api.server
```

**Terminal 2 — Bot Discord:**
```
cd /d D:\Proyectos\Yggdrasil\Asgard\Lilith\Discord
python bot.py
```

Espera a que la API diga que está escuchando y el bot que está "ready".

**Si el puerto 8000 ya está en uso** (error `[winerror 10048] solo se permite un uso...`):
- Cierra la otra ventana/terminal donde corre la API, o
- Libera el puerto (PowerShell como admin): `Get-NetTCPConnection -LocalPort 8000 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }`, o
- Usa otro puerto: `set LILITH_API_PORT=8001` antes de arrancar, y en el bot configura `LILITH_API_URL=http://127.0.0.1:8001`.

**Si ves "IPC no disponible" / "Failed to connect to IPC"**: es normal si solo arrancas la API (sin el Core `main.py`). La API y Discord funcionan en modo standalone. Para usar la UI de escritorio con sesiones, arranca también el Core.

---

## 2. Probar API (navegador o curl)

Pega cada URL en el navegador (con la API en marcha):

**Status:**
```
http://localhost:8000/api/status
```

**Tools-status (3.7):**
```
http://localhost:8000/api/discord/tools-status
```

**Export memoria del hilo** (cambia `CHANNEL_ID` por un ID real si tienes; si no, usa uno de prueba):
```
http://localhost:8000/api/discord/thread-memory?channel_id=123456789&thread_id=
```

---

## 3. Tests automáticos (PowerShell)

Desde la carpeta Core:

```
Set-Location D:\Proyectos\Yggdrasil\Asgard\Lilith\Core; python -m pytest Tests/test_planner_intents_36.py -v
```

---

## 4. Mensajes para pegar en Discord

Usa el **canal donde Lilith responde** o **DM con el bot**. Pega estos mensajes **uno por uno** y comprueba que la respuesta sea la esperada.

### 4.1 Un solo mensaje (no “Enviado a X”)

Si usas **slash**, escribe en Discord:

```
/odin dime algo breve sobre el proyecto
```

**Comprueba:** Solo un mensaje con la respuesta de Odín y pie «Respondido por Odín» (no debe aparecer «Enviado a Odín» en el canal).

### 4.2 Mensaje normal (owner)

Pega en el canal o DM:

```
Hola
```

**Comprueba:** Una respuesta tipo «Lilith en línea. ¿En qué puedo ayudarte, Ainz?» (o similar).

### 4.3 Sin plantillas ENFOQUE/RIESGOS (DM owner)

Pega en **DM con Lilith**:

```
¿Qué tal estás?
```

**Comprueba:** Respuesta natural, sin bloques ENFOQUE/RIESGOS/EJECUCIÓN.

### 4.4 Memoria del hilo

En el **mismo canal o hilo**, pega primero:

```
Me llamo Ainz y estoy probando la memoria del hilo.
```

Luego, en el **mismo sitio**:

```
¿Cómo me llamo?
```

**Comprueba:** La respuesta menciona “Ainz” o el contexto que acabas de dar.

### 4.5 Buscar en memoria

Pega (en DM o canal de owner):

```
Busca en tu memoria a momi
```

**Comprueba:** Respuesta sobre memoria (Lucifer), no “archivo no encontrado” ni listado de directorio.

### 4.6 Lista de puntos (no list_directory)

Pega:

```
Lista 3-5 puntos para mejorar la experiencia en Discord
```

**Comprueba:** Respuesta con una lista de puntos en texto; **no** un listado de archivos/carpetas.

### 4.7 Kimi / Albedo sin crudo

Pega (solo si tienes Kimi CLI configurado):

```
Abre el cli de Kimi y dime hola en una frase
```

**Comprueba:** Texto legible; **no** líneas como `TurnBegin(`, `ThinkPart(`, etc.

### 4.8 Triggers “invoca” / “pregunta”

Pega:

```
Invoca a Lucifer y pregúntale qué opina del dark fantasy
```

**Comprueba:** Respuesta de Lucifer (tono/voz coherente).

### 4.9 Límite por rol (canal público)

Si tienes un **canal público** donde Lilith responde con rol limitado, pega un mensaje que suela generar respuestas muy largas y comprueba que se corte con algo tipo «… (respuesta recortada)» si aplica.

---

## 5. Checklist rápido

Marca mentalmente o en papel:

- [ ] API arranca sin error
- [ ] Bot arranca y aparece en línea
- [ ] `http://localhost:8000/api/discord/tools-status` devuelve JSON
- [ ] Mensaje «Hola» → una respuesta con embed
- [ ] Slash `/odin algo` → un solo mensaje con respuesta de Odín (no «Enviado a Odín»)
- [ ] Respuesta de Kimi/Albedo sin TurnBegin/ThinkPart
- [ ] «Lista 3-5 puntos…» → lista de puntos, no listado de directorio
- [ ] «Busca en tu memoria a momi» → respuesta de memoria, no error de archivo

---

## 6. Si algo falla

- **Timeout / no responde:** Revisa que la API no esté colgada; en la ventana de la API deberían verse logs de las peticiones.
- **Doble mensaje con slash:** Debe salir solo «Listo.» en ephemeral y un mensaje con la respuesta; si no, revisa que estés con la versión actual de `command_handler.py`.
- **TurnBegin/ThinkPart en la respuesta:** Debe estar activo el normalizador en la API; reinicia la API.
- **«No autorizado»:** Revisa `Config/discord_roles.json`, `Discord/data/allowed_channels.json` y que tu usuario esté como owner (AINZ_DISCORD_ID en `.env` del bot).
