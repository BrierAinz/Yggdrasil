# ⚰️ Reglas de Helheim - Cripta de Proyectos

> **Propósito:** Proyectos abandonados, versiones antiguas, código muerto

---

## ✅ Sí Permitido
- Proyectos abandonados
- Versiones viejas de sistemas
- Código que ya no funciona
- Intentos fallidos con valor histórico

## ❌ Prohibido
- Desarrollo activo (no se edita nada aquí)
- Proyectos que pueden resucitarse (usar fork)
- Datos sensibles (incluso muertos)
- Archivos temporales

---

## Estructura
```
Helheim/
├── README.md
├── Graveyard.md        # Índice de lo que murió y por qué
├── Abandoned/          # Proyectos abandonados
├── Deprecated/         # Versiones viejas
│   ├── Lilith_v1.0/
│   └── Cortana_v2.0/
└── Obsolete/           # Código que ya no funciona
```

---

## Ritual de Entrada

Cuando un proyecto muere:

1. **Último commit**: `[ARCHIVADO] Razón: X`
2. **Mover a Helheim/** manteniendo estructura
3. **Actualizar Graveyard.md**:
   ```markdown
   ## 2026-03-21 - Proyecto X
   - **Fecha de muerte**: 2026-03-21
   - **Razón**: [abandono/fallo/reemplazo]
   - **Lecciones**: Lo que se aprendió
   - **Rescatable**: Sí/No - Qué se podría reusar
   ```

---

## Reglas Específicas

1. **Read-only**: No se desarrolla, solo se archiva
2. **Epitafio obligatorio**: Cada proyecto necesita razón de muerte
3. **Resucitación posible**: Como fork nuevo, no revival in-place
4. **Revisión anual**: ¿Algo merece resucitar?

---

*Cripta de Proyectos - Aquí descansan los caídos*
