# Reglas de Yggdrasil

Leyes fundamentales del ecosistema. Todos los realms las obedecen.

---

## Reglas del Monorepo

1. **Cada realm tiene un proposito.** No mezclar responsabilidades entre reinos.
2. **Svartalfheim es la fuente de verdad.** Toda documentacion vive ahi. Los READMEs de otros realms son resumenes.
3. **Los paquetes lilith-* son modulares.** Cada paquete tiene su propio pyproject.toml y puede instalarse independientemente.
4. **Los scripts van en Scripts/ o Svartalfheim/Scripts/.** No scripts sueltos en la raiz.
5. **Los planes siguen el formato plan-NN-*.md.** Se archivan en plans/ con numeracion secuencial.
6. **Los proyectos muertos van a Helheim.** No se eliminan, se archivan con razon y fecha.
7. **.env nunca se commitea.** El .gitignore lo excluye. Usar .env.example como plantilla.
8. **Los modelos y datasets van a Niflheim.** Excluidos de git por .gitignore.
9. **Python >=3.11.** El ecosistema requiere Python 3.11 o superior.
10. **Commits con prefijo de realm.** Formato: `[REALM] tipo: descripcion`

---

## Convenciones de Commits

```
[ASGARD] feat: nuevo modulo en lilith-core
[MUSPELHEIM] fix: corregir generacion de dataset
[SVARTALFHEIM] docs: actualizar documentacion de API
[ALL] chore: actualizar dependencias
```

**Tipos:** feat, fix, docs, style, refactor, test, chore

---

## Organizacion por Realm

| Realm | Contenido permitido | No permitido |
|-------|-------------------|--------------|
| Asgard | Paquetes lilith-*, pyproject.toml | Docs, scripts sueltos |
| Vanaheim | Frameworks de agentes | Implementaciones especificas |
| Alfheim | UIs, dashboards | Logica de backend |
| Svartalfheim | Docs, scripts, planes, wiki, notes | Codigo ejecutable de aplicaciones |
| Muspelheim | Proyectos WIP, experimentos | Proyectos estables (van a su realm) |
| Niflheim | Modelos, datasets, assets | Codigo |
| Helheim | Archivos muertos, cuarentena | Proyectos activos |
| Jotunheim | Proyectos de gran escala | Proyectos pequenos |
| Midgard | Proyectos personales | Proyectos del ecosistema |

---

## Reglas de Documentacion

1. **README.md en cada realm.** Minimo: descripcion, estructura, estado.
2. **README.md en cada paquete.** Minimo: nombre, version, descripcion.
3. **CHANGELOG.md en root.** Formato Keep a Changelog.
4. **REGLAS.md en Svartalfheim.** Leyes especificas del reino de documentacion.

---

## Reglas de Seguridad

1. **Nunca commitear credenciales.** API keys, tokens, passwords van en .env.
2. **Los agentes tienen permisos limitados.** Definidos en agent_permissions.json.
3. **Helheim es solo lectura.** Los archivos archivados no se modifican.
4. **Los datasets grandes van a Niflheim.** Excluidos de git.

---

*Reglas actualizadas: 2026-05-29*
