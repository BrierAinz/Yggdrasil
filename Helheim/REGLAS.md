# ⚖️ REGLAS — Helheim

Leyes del reino de los muertos. Lo que entra, no sale sin permiso del Arquitecto.

## 📜 Reglas del Reino

1. **Helheim es exclusivamente de archivo.** No se desarrolla, no se modifica, no se ejecuta nada aquí. Es el reposo final.
2. **Los artefactos se comprimen.** Los directorios legacy se almacenan como archivos `.tar.gz`. No se mantienen directorios expandidos en Helheim a menos que el Arquitecto lo ordene.
3. **Graveyard.md es el registro sagrado.** Todo proyecto que llegue a Helheim debe tener su epitafio registrado en `Graveyard.md`: nombre, fecha de muerte, causa, y si aplica, ubicación del archivo comprimido.
4. **No se elimina permanentemente sin registro.** Si algo se purga (como ocurrió con `Quarantine_2026-04-29/`), se documenta en Graveyard.md que existió y fue destruido.
5. **La resurrección es posible pero rara.** Solo el Arquitecto puede autorizar sacar un proyecto de Helheim. Si se hace, se documenta en Graveyard.md con fecha y destino.
6. **Archives_Lilith_Legacy es un archivo, NO un directorio.** Es un tar.gz de 852MB. No se extrae in situ. Si se necesita contenido, se extre temporalmente en otro reino y se trabaja ahí.

## 📂 Directorios y Archivos

| Path | Tipo | Descripción |
|---|---|---|
| `Archives_Lilith_Legacy_2026-04-29.tar.gz` | Archivo comprimido (852MB) | El monolito legado de Lilith, sellado. **No es un directorio — no se navega como tal.** |
| `Graveyard.md` | Documento | Registro de proyectos muertos. Epitafios del ecosistema. |
| ~~`Quarantine_2026-04-29/`~~ | **PURGADO** | Fue evaluado y destruido. Ya no existe. Documentado en Graveyard.md. |

## 🔄 Triggers de Migración (Entrada)

| Si un artefecto… | Entonces tráelo a Helheim como… |
|---|---|
| Un proyecto es abandonado sin esperanza de resurrección | `archivo.tar.gz` + epitafio en Graveyard.md |
| Un directorio legacy que ya no se consulta | `archivo.tar.gz` + epitafio en Graveyard.md |
| Un dataset o modelo obsoleto | Archivo comprimido bajo naming de fecha |
| Una rama de experimentación fallida | Archivo comprimido + lección aprendida en Graveyard.md |

## 🔄 Triggers de Migración (Salida)

| Si el Arquitecto decide… | Entonces… |
|---|---|
| Resucitar un proyecto | Se extrae del tar.gz, se mueve al reino destino, se registra la resurrección en Graveyard.md |
| Consultar contenido del archivo | Se extrae temporalmente en workspace, nunca se modifica el tar.gz original |

## 🚫 Prohibiciones

- ❌ **Desarrollo activo** — Helheim no es workspace; es cementerio
- ❌ **Directorios expandidos** — Todo se comprime en tar.gz
- ❌ **Modificación de archivos archivados** — El muerto no se reescribe
- ❌ **Eliminar el tar.gz sin consolidar Graveyard.md** — Todo debe tener epitafio
- ❌ **Crear subcarpetas de proyectos activos** — Solo archivos comprimidos y documentación

---

*Los muertos no hablan. Pero Graveyard.md habla por ellos. Y lo que está escrito en Helheim, solo el Arquitecto puede deshacerlo.*
